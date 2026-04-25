"""消息服务总入口。"""

from .config_loader import load_service_config, load_service_config_strict
from .wechat_client import WechatClientError, at_all, send_file, send_text
from .jubensha_booking import (
    BookingPosterError,
    download_poster_image,
    fetch_booking_poster_url,
    generate_booking_poster,
    send_booking_poster_to_chat,
    send_booking_poster_to_chats,
    send_poster_to_chat,
)
from .log_stream import get_service_log_history, set_service_log_sink
from .registry import dispatch_message_to_services, get_service_manager, shutdown_service_manager
from .registry import set_service_wechat_client

__all__ = [
    "BookingPosterError",
    "WechatClientError",
    "at_all",
    "dispatch_message_to_services",
    "download_poster_image",
    "fetch_booking_poster_url",
    "generate_booking_poster",
    "get_service_manager",
    "get_service_log_history",
    "load_service_config",
    "load_service_config_strict",
    "send_file",
    "send_booking_poster_to_chat",
    "send_booking_poster_to_chats",
    "send_poster_to_chat",
    "send_text",
    "set_service_wechat_client",
    "set_service_log_sink",
    "shutdown_service_manager",
]
