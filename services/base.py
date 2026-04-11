"""服务层公共类型。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

MessagePayload = dict[str, Any]


class MessageService(ABC):
    """消息驱动服务的最小接口。"""

    name: str

    @abstractmethod
    def handle_message(self, message: MessagePayload) -> None:
        """处理一条消息。"""
