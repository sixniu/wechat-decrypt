"""剧本杀拼本消息处理服务。"""

from __future__ import annotations

import hashlib
import threading
import time
import datetime as dt
from typing import Any

from zhipu_chat_demo import PROVIDER_ZHIPU, JubenshaExtractionError, extract_jubensha

from ..base import MessagePayload, MessageService
from ..log_stream import emit_service_log
from .constants import DISCOUNT_LABELS
from .mysql_client import JubenshaMySQLClient


class JubenshaBookingService(MessageService):
    """监听关键词消息，提取并写入剧本杀拼本数据。"""

    name = "jubensha_booking"

    def __init__(
        self,
        *,
        mysql_client: JubenshaMySQLClient,
        monitored_chatroom_ids: tuple[str, ...],
        trigger_keywords: tuple[str, ...],
        allowed_time_range: tuple[str, str],
        provider: str = PROVIDER_ZHIPU,
    ) -> None:
        """初始化剧本杀拼本消息服务。

        参数:
        - mysql_client: MySQL 访问客户端，负责原始消息去重和业务数据写入。
        - monitored_chatroom_ids: 允许进入提取流程的微信群 ID 列表。
        - trigger_keywords: 触发消息提取的关键词列表。
        - allowed_time_range: 每日允许处理的时间范围，格式为 `(start, end)`，值为 `HH:MM`。
        - provider: AI 提取服务提供商名称。
        """
        self._mysql_client = mysql_client
        self._provider = provider
        self._monitored_chatroom_ids = monitored_chatroom_ids
        self._trigger_keywords = trigger_keywords
        self._allowed_time_range = self._parse_allowed_time_range(allowed_time_range)
        self._stats_lock = threading.Lock()
        self._stats_bucket_minute = self._current_minute()
        self._stats = self._empty_stats()

    def handle_message(self, message: MessagePayload) -> None:
        """处理一条群聊消息，并在满足条件时提取剧本杀拼本结构化数据。

        参数:
        - message: 监听层传入的标准化消息对象，包含群 ID、发送人、内容、消息类型等字段。

        关键副作用:
        - 命中条件时会写入原始消息表、调用 AI、写入业务表、输出服务日志。
        """
        trace_id = self._build_trace_id(message)

        if not message.get("is_group"):
            self._record_stat("skip_non_group")
            return

        chatroom_id = self._resolve_chatroom_id(message)
        if chatroom_id not in self._monitored_chatroom_ids:
            self._record_stat("skip_unmonitored_group")
            return

        content = self._extract_content(message)
        if not content:
            self._record_stat("skip_non_text")
            return

        matched_keywords = [
            keyword for keyword in self._trigger_keywords if keyword in content
        ]
        if not matched_keywords:
            self._record_stat("skip_no_keyword")
            return
        if not self._is_within_allowed_time_range():
            self._record_stat("skip_outside_allowed_time")
            return

        sender_name, sender_wx_id = self._resolve_sender(message)
        if not sender_wx_id:
            self._record_stat("skip_no_sender")
            return
        sender_wechat_no = str(message.get("wechat_no") or "").strip()
        sender_wechat_no_label = sender_wechat_no or "不是好友"

        self._record_stat("matched")
        self._log(
            trace_id,
            f"命中处理: sender={sender_name or '-'} sender_id={sender_wx_id} "
            f"wechat_no={sender_wechat_no_label} "
            f"keywords={matched_keywords} content={content[:80]!r}",
            data={
                "chat_id": str(message.get("chat_id") or message.get("username") or ""),
                "sender": sender_name,
                "sender_id": sender_wx_id,
                "wechat_no": sender_wechat_no_label,
                "content": content,
                "matched_keywords": matched_keywords,
            },
        )

        inserted = self._mysql_client.reserve_raw_message(
            sender_name=sender_name,
            sender_wx_id=sender_wx_id,
            content=content,
        )
        if not inserted:
            self._record_stat("dedup_raw")
            return

        self._record_stat("raw_inserted")
        self._log(
            trace_id,
            "原始消息已写入 jubensha_all_content，开始请求 AI",
            data={
                "sender_name": sender_name,
                "sender_wx_id": sender_wx_id,
                "content": content,
            },
        )

        try:
            result = extract_jubensha(content, provider=self._provider)
        except JubenshaExtractionError as exc:
            self._record_stat("ai_failed")
            self._log(trace_id, f"AI 提取失败: {exc}", kind="error")
            return

        data = result.get("data", [])
        self._record_stat("ai_succeeded")
        self._record_stat("ai_rows", len(data))
        self._log(
            trace_id,
            f"AI 提取成功: 返回 {len(data)} 条结构化数据",
            data={
                "provider": result.get("provider"),
                "raw_text": result.get("raw_text"),
                "items": data,
            },
        )

        for index, item in enumerate(data, start=1):
            booking_item = self._normalize_booking_item(
                item,
                sender_name,
                sender_wx_id,
                sender_wechat_no,
            )
            self._mysql_client.upsert_booking(booking_item)
            self._record_stat("booking_upserted")
            self._log(
                trace_id,
                f"业务入库完成[{index}/{len(data)}]: "
                f"booking_time={booking_item['booking_time']} "
                f"store={booking_item['store_name'] or '-'} "
                f"script={booking_item['script_name']}",
                data=booking_item,
            )

        self._log(trace_id, "处理完成")

    @staticmethod
    def _extract_content(message: MessagePayload) -> str:
        """从标准化消息对象中提取文本内容。"""
        if message.get("type") != "文本":
            return ""
        content = message.get("content", "")
        return content.strip() if isinstance(content, str) else ""

    @staticmethod
    def _resolve_sender(message: MessagePayload) -> tuple[str, str]:
        """从消息对象中解析发送人显示名和发送人微信内部 ID。"""
        sender_name = str(message.get("sender") or "").strip()
        sender_wx_id = str(message.get("sender_id") or "").strip()
        return sender_name, sender_wx_id

    @staticmethod
    def _resolve_chatroom_id(message: MessagePayload) -> str:
        """从消息对象中解析群聊 ID。"""
        return str(message.get("chat_id") or message.get("username") or "").strip()

    @staticmethod
    def _normalize_booking_item(
        item: dict[str, Any],
        sender_name: str,
        sender_wx_id: str,
        sender_wechat_no: str = "",
    ) -> dict[str, str]:
        """把 AI 返回的结构化字段标准化为数据库写入对象。"""
        discount_type = str(item.get("discount_type", "normal")).strip().lower()
        return {
            "user_name": sender_name,
            "user_id": sender_wx_id,
            "booking_time": str(item.get("booking_time") or "").strip(),
            "store_name": str(item.get("store_name") or "").strip(),
            "script_name": str(item.get("script_name") or "").strip(),
            "script_details": str(item.get("script_details") or "").strip(),
            "discount_type": DISCOUNT_LABELS.get(discount_type, "正常"),
            "wechat_no": sender_wechat_no,
        }

    @staticmethod
    def _build_trace_id(message: MessagePayload) -> str:
        """根据消息关键字段构造稳定的链路追踪 ID。"""
        chat_id = str(message.get("chat_id") or message.get("username") or "-").strip()
        timestamp = str(message.get("timestamp") or "-").strip()
        sender_id = str(message.get("sender_id") or "-").strip()
        content = str(message.get("content") or "").strip()
        raw = f"{chat_id}|{timestamp}|{sender_id}|{content}"
        return f"jb-{hashlib.md5(raw.encode('utf-8')).hexdigest()[:10]}"

    @staticmethod
    def _log(
        trace_id: str,
        message: str,
        *,
        kind: str = "log",
        data: Any = None,
    ) -> None:
        """输出服务日志并同步推送到服务日志流。"""
        print(f"[services][jubensha][{trace_id}] {message}", flush=True)
        emit_service_log(
            service="jubensha_booking",
            trace_id=trace_id,
            message=message,
            kind=kind,
            data=data,
        )

    @staticmethod
    def _current_minute() -> int:
        """返回当前时间所属的分钟桶，用于分钟级统计汇总。"""
        return int(time.time() // 60)

    @staticmethod
    def _empty_stats() -> dict[str, int]:
        """创建空的分钟统计计数器。"""
        return {
            "matched": 0,
            "skip_non_group": 0,
            "skip_unmonitored_group": 0,
            "skip_non_text": 0,
            "skip_no_keyword": 0,
            "skip_outside_allowed_time": 0,
            "skip_no_sender": 0,
            "dedup_raw": 0,
            "raw_inserted": 0,
            "ai_succeeded": 0,
            "ai_failed": 0,
            "ai_rows": 0,
            "booking_upserted": 0,
        }

    def _record_stat(self, key: str, value: int = 1) -> None:
        """记录一项统计计数，并在分钟切换时输出上一分钟汇总。"""
        with self._stats_lock:
            current_minute = self._current_minute()
            if current_minute != self._stats_bucket_minute:
                self._flush_stats_locked()
                self._stats_bucket_minute = current_minute
                self._stats = self._empty_stats()
            self._stats[key] += value

    def _flush_stats_locked(self) -> None:
        """输出当前分钟汇总日志。

        调用方要求已经持有 `_stats_lock`，因此这里不再重复加锁。
        """
        if not any(self._stats.values()):
            return
        minute_text = time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(self._stats_bucket_minute * 60),
        )
        summary_data = {
            "命中处理": self._stats["matched"],
            "跳过非群聊": self._stats["skip_non_group"],
            "跳过非监控群聊": self._stats["skip_unmonitored_group"],
            "跳过非文本": self._stats["skip_non_text"],
            "跳过无关键词": self._stats["skip_no_keyword"],
            "跳过非业务时段": self._stats["skip_outside_allowed_time"],
            "跳过无发送人": self._stats["skip_no_sender"],
            "原始去重命中": self._stats["dedup_raw"],
            "原始新增": self._stats["raw_inserted"],
            "AI成功": self._stats["ai_succeeded"],
            "AI失败": self._stats["ai_failed"],
            "AI返回条数": self._stats["ai_rows"],
            "业务入库条数": self._stats["booking_upserted"],
        }
        summary = (
            f"[服务][剧本杀][分钟汇总][{minute_text}] "
            f"命中处理={summary_data['命中处理']} "
            f"跳过非群聊={summary_data['跳过非群聊']} "
            f"跳过非监控群聊={summary_data['跳过非监控群聊']} "
            f"跳过非文本={summary_data['跳过非文本']} "
            f"跳过无关键词={summary_data['跳过无关键词']} "
            f"跳过非业务时段={summary_data['跳过非业务时段']} "
            f"跳过无发送人={summary_data['跳过无发送人']} "
            f"原始去重命中={summary_data['原始去重命中']} "
            f"原始新增={summary_data['原始新增']} "
            f"AI成功={summary_data['AI成功']} "
            f"AI失败={summary_data['AI失败']} "
            f"AI返回条数={summary_data['AI返回条数']} "
            f"业务入库条数={summary_data['业务入库条数']}"
        )
        print(summary, flush=True)
        emit_service_log(
            service="jubensha_booking",
            trace_id=f"summary|{minute_text}",
            message=summary,
            kind="summary",
            data=summary_data,
        )

    def _is_within_allowed_time_range(self) -> bool:
        """判断当前本地时间是否落在允许处理的业务时间范围内。"""
        now_struct = time.localtime()
        current_time = dt.time(hour=now_struct.tm_hour, minute=now_struct.tm_min)
        start_time, end_time = self._allowed_time_range
        return start_time <= current_time <= end_time

    @staticmethod
    def _parse_allowed_time_range(allowed_time_range: tuple[str, str]) -> tuple[dt.time, dt.time]:
        """把 `HH:MM` 时间范围配置解析为 time 对象元组。"""
        start_raw, end_raw = allowed_time_range
        return (
            JubenshaBookingService._parse_hhmm(start_raw),
            JubenshaBookingService._parse_hhmm(end_raw),
        )

    @staticmethod
    def _parse_hhmm(raw: str) -> dt.time:
        """把单个 `HH:MM` 字符串解析为 `datetime.time`。"""
        hour_text, minute_text = str(raw).split(":", 1)
        return dt.time(hour=int(hour_text), minute=int(minute_text))
