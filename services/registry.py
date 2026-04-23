"""服务注册表。"""

from __future__ import annotations

from typing import Any

from zhipu_chat_demo import PROVIDER_ZHIPU

from .config_loader import load_service_config
from .jubensha_booking import JubenshaBookingService, JubenshaMySQLClient
from .manager import ServiceManager

_service_manager: ServiceManager | None = None


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

    mysql_client = JubenshaMySQLClient(
        mysql_cfg,
        raw_table=jubensha_cfg.get("raw_table", "jubensha_all_content"),
        booking_table=jubensha_cfg.get("booking_table", "jubensha_booking"),
    )
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
            monitored_chatroom_ids=_normalize_chatroom_ids(
                jubensha_cfg.get("monitored_chatroom_ids", [])
            ),
            trigger_keywords=tuple(jubensha_cfg.get("trigger_keywords", [])),
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
