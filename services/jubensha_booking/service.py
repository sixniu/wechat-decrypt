"""剧本杀拼本消息处理服务。"""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

from zhipu_chat_demo import PROVIDER_ZHIPU, JubenshaExtractionError, extract_jubensha

from ..base import MessagePayload, MessageService
from ..log_stream import emit_service_log
from .constants import DISCOUNT_LABELS, TRIGGER_KEYWORDS
from .mysql_client import JubenshaMySQLClient


class JubenshaBookingService(MessageService):
    """监听关键词消息，提取并写入剧本杀拼本数据。"""

    name = "jubensha_booking"

    def __init__(
        self,
        *,
        mysql_client: JubenshaMySQLClient,
        provider: str = PROVIDER_ZHIPU,
    ) -> None:
        self._mysql_client = mysql_client
        self._provider = provider
        self._stats_lock = threading.Lock()
        self._stats_bucket_minute = self._current_minute()
        self._stats = self._empty_stats()

    def handle_message(self, message: MessagePayload) -> None:
        trace_id = self._build_trace_id(message)

        if not message.get("is_group"):
            self._record_stat("skip_non_group")
            self._log(trace_id, "跳过: 非群聊消息")
            return

        content = self._extract_content(message)
        if not content:
            self._record_stat("skip_non_text")
            self._log(trace_id, "跳过: 非文本消息或内容为空")
            return

        matched_keywords = [keyword for keyword in TRIGGER_KEYWORDS if keyword in content]
        if not matched_keywords:
            self._record_stat("skip_no_keyword")
            self._log(trace_id, "跳过: 未命中关键词")
            return

        sender_name, sender_wx_id = self._resolve_sender(message)
        if not sender_wx_id:
            self._record_stat("skip_no_sender")
            self._log(trace_id, "跳过: sender_id 为空")
            return

        self._record_stat("matched")
        self._log(
            trace_id,
            f"命中处理: sender={sender_name or '-'} sender_id={sender_wx_id} "
            f"keywords={matched_keywords} content={content[:80]!r}",
            data={
                "chat_id": str(message.get("chat_id") or message.get("username") or ""),
                "sender": sender_name,
                "sender_id": sender_wx_id,
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
            self._log(trace_id, "原始消息去重命中: jubensha_all_content 已存在，跳过 AI")
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
            booking_item = self._normalize_booking_item(item, sender_name, sender_wx_id)
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
        if message.get("type") != "文本":
            return ""
        content = message.get("content", "")
        return content.strip() if isinstance(content, str) else ""

    @staticmethod
    def _resolve_sender(message: MessagePayload) -> tuple[str, str]:
        sender_name = str(message.get("sender") or "").strip()
        sender_wx_id = str(message.get("sender_id") or "").strip()
        return sender_name, sender_wx_id

    @staticmethod
    def _normalize_booking_item(
        item: dict[str, Any],
        sender_name: str,
        sender_wx_id: str,
    ) -> dict[str, str]:
        discount_type = str(item.get("discount_type", "normal")).strip().lower()
        return {
            "user_name": sender_name,
            "user_id": sender_wx_id,
            "booking_time": str(item.get("booking_time") or "").strip(),
            "store_name": str(item.get("store_name") or "").strip(),
            "script_name": str(item.get("script_name") or "").strip(),
            "script_details": str(item.get("script_details") or "").strip(),
            "discount_type": DISCOUNT_LABELS.get(discount_type, "正常"),
            "wechat_no": str(item.get("wechat_no") or "").strip(),
        }

    @staticmethod
    def _build_trace_id(message: MessagePayload) -> str:
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
        return int(time.time() // 60)

    @staticmethod
    def _empty_stats() -> dict[str, int]:
        return {
            "matched": 0,
            "skip_non_group": 0,
            "skip_non_text": 0,
            "skip_no_keyword": 0,
            "skip_no_sender": 0,
            "dedup_raw": 0,
            "raw_inserted": 0,
            "ai_succeeded": 0,
            "ai_failed": 0,
            "ai_rows": 0,
            "booking_upserted": 0,
        }

    def _record_stat(self, key: str, value: int = 1) -> None:
        with self._stats_lock:
            current_minute = self._current_minute()
            if current_minute != self._stats_bucket_minute:
                self._flush_stats_locked()
                self._stats_bucket_minute = current_minute
                self._stats = self._empty_stats()
            self._stats[key] += value

    def _flush_stats_locked(self) -> None:
        if not any(self._stats.values()):
            return
        minute_text = time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(self._stats_bucket_minute * 60),
        )
        summary_data = {
            "命中处理": self._stats["matched"],
            "跳过非群聊": self._stats["skip_non_group"],
            "跳过非文本": self._stats["skip_non_text"],
            "跳过无关键词": self._stats["skip_no_keyword"],
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
            f"跳过非文本={summary_data['跳过非文本']} "
            f"跳过无关键词={summary_data['跳过无关键词']} "
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
