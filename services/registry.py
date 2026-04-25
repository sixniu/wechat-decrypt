"""服务注册表。"""

from __future__ import annotations

from typing import Any

from zhipu_chat_demo import PROVIDER_ZHIPU

from .config_loader import load_service_config
from .jubensha_booking import (
    FreeDiscountNotifier,
    JubenshaBookingService,
    JubenshaMySQLClient,
)
from .manager import ServiceManager

_service_manager: ServiceManager | None = None
_wechat_client: Any | None = None


def set_service_wechat_client(wx: Any | None) -> None:
    """设置服务层可复用的微信客户端实例。

    参数:
    - wx: 启动入口初始化好的 WeChat 实例；传 None 表示清空。

    返回值:
    - 无返回值；后续创建服务管理器时会把该实例注入需要发送微信消息的服务。
    """
    global _wechat_client
    _wechat_client = wx


def get_service_manager() -> ServiceManager:
    """获取全局服务管理器。"""
    global _service_manager
    if _service_manager is None:
        services = _build_services()
        print(
            f"[services] 已初始化服务管理器，启用服务数: {len(services)}",
            flush=True,
        )
        _service_manager = ServiceManager(services)
    return _service_manager


def dispatch_message_to_services(message: dict[str, Any]) -> None:
    """将消息投递给已启用的服务。"""
    get_service_manager().submit_message(message)


def shutdown_service_manager(*, wait: bool = False) -> None:
    """关闭全局服务管理器。"""
    global _service_manager
    if _service_manager is None:
        return
    _service_manager.shutdown(wait=wait)
    _service_manager = None


def _build_services() -> list[object]:
    cfg = load_service_config()
    mysql_cfg = cfg.get("mysql", {})
    services_cfg = cfg.get("services", {})
    jubensha_cfg = services_cfg.get("jubensha_booking", {})
    if not jubensha_cfg.get("enabled"):
        print("[services] jubensha_booking 未启用: enabled=false", flush=True)
        return []

    required = ("host", "user", "password", "database")
    missing = [key for key in required if not str(mysql_cfg.get(key, "")).strip()]
    if missing:
        print(
            f"[services] jubensha_booking 未启用: mysql 缺少配置 {', '.join(missing)}",
            flush=True,
        )
        return []

    chatroom_ids = _normalize_chatroom_ids(
        jubensha_cfg.get("monitored_chatroom_ids", [])
    )
    mysql_client = JubenshaMySQLClient(
        mysql_cfg,
        raw_table=jubensha_cfg.get("raw_table", "jubensha_all_content"),
        booking_table=jubensha_cfg.get("booking_table", "jubensha_booking"),
    )
    free_discount_notifier = _build_free_discount_notifier(jubensha_cfg)
    print(
        "[services] jubensha_booking 已启用: "
        f"provider={jubensha_cfg.get('provider', PROVIDER_ZHIPU)}, "
        f"raw_table={jubensha_cfg.get('raw_table', 'jubensha_all_content')}, "
        f"booking_table={jubensha_cfg.get('booking_table', 'jubensha_booking')}, "
        f"monitored_chatrooms={len(jubensha_cfg.get('monitored_chatroom_ids', []))}, "
        f"trigger_keywords={len(jubensha_cfg.get('trigger_keywords', []))}",
        flush=True,
    )
    return [
        JubenshaBookingService(
            mysql_client=mysql_client,
            provider=jubensha_cfg.get("provider", PROVIDER_ZHIPU),
            monitored_chatroom_ids=chatroom_ids,
            trigger_keywords=tuple(jubensha_cfg.get("trigger_keywords", [])),
            allowed_time_range=_normalize_allowed_time_range(
                jubensha_cfg.get("allowed_time_range", {})
            ),
            free_discount_notifier=free_discount_notifier,
        )
    ]


def _normalize_chatroom_ids(raw_chatrooms: object) -> tuple[str, ...]:
    """兼容字符串列表和带 name 的对象列表。"""
    chatroom_ids: list[str] = []
    if not isinstance(raw_chatrooms, list):
        return ()

    for item in raw_chatrooms:
        if isinstance(item, str):
            chatroom_id = item.strip()
        elif isinstance(item, dict):
            chatroom_id = str(item.get("id") or "").strip()
        else:
            chatroom_id = ""

        if chatroom_id:
            chatroom_ids.append(chatroom_id)

    return tuple(chatroom_ids)


def _build_free_discount_notifier(jubensha_cfg: dict[str, Any]) -> FreeDiscountNotifier | None:
    """按配置创建免单通知器。

    参数:
    - jubensha_cfg: `services.jubensha_booking` 配置对象。

    返回值:
    - 配置启用且 wx 已初始化时返回通知器；否则返回 None。
    """
    notifier_cfg = jubensha_cfg.get("free_discount_notifier", {})
    if not isinstance(notifier_cfg, dict) or not notifier_cfg.get("enabled"):
        return None
    if _wechat_client is None:
        print("[services][jubensha][free] 未启动: wx 未初始化", flush=True)
        return None

    return FreeDiscountNotifier(
        wx=_wechat_client,
        target_chats=_normalize_target_chats(notifier_cfg),
        exact=bool(notifier_cfg.get("exact", False)),
    )


def _normalize_target_chats(raw_cfg: dict[str, Any]) -> tuple[str, ...]:
    """规范化免单通知目标群聊配置。

    参数:
    - raw_cfg: 免单通知配置对象。

    返回值:
    - 返回去掉空值后的目标群聊名称元组；为空时通知器不会发送。
    """
    raw_targets = raw_cfg.get("target_chats")
    if isinstance(raw_targets, list):
        targets = [str(item).strip() for item in raw_targets if str(item).strip()]
        if targets:
            return tuple(targets)

    return ()


def _normalize_allowed_time_range(raw_range: object) -> tuple[str, str]:
    """规范化允许处理的业务时间范围配置。

    参数:
    - raw_range: `services.config.json` 中的 `allowed_time_range` 配置对象。

    返回值:
    - 返回 `(start, end)` 二元组，格式均为 `HH:MM`。
    """
    if not isinstance(raw_range, dict):
        return ("09:30", "20:00")

    start = str(raw_range.get("start") or "09:30").strip()
    end = str(raw_range.get("end") or "20:00").strip()
    return (start, end)
