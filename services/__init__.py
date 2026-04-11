"""消息服务总入口。"""

from .config_loader import load_service_config
from .log_stream import get_service_log_history, set_service_log_sink
from .registry import dispatch_message_to_services, get_service_manager, shutdown_service_manager

__all__ = [
    "dispatch_message_to_services",
    "get_service_manager",
    "get_service_log_history",
    "load_service_config",
    "set_service_log_sink",
    "shutdown_service_manager",
]
