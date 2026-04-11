"""服务调度管理器。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from .base import MessagePayload, MessageService


class ServiceManager:
    """把消息异步分发给多个子服务。"""

    def __init__(
        self,
        services: Iterable[MessageService],
        *,
        max_workers: int = 4,
    ) -> None:
        self._services = tuple(services)
        self._shutdown = False
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="svc",
        )

    def submit_message(self, message: MessagePayload) -> None:
        """异步投递消息给所有服务。"""
        if not self._services or self._shutdown:
            return

        payload = dict(message)
        for service in self._services:
            try:
                self._executor.submit(self._safe_handle, service, payload)
            except RuntimeError:
                self._shutdown = True
                return

    def shutdown(self, *, wait: bool = False) -> None:
        """关闭服务线程池。"""
        if self._shutdown:
            return
        self._shutdown = True
        self._executor.shutdown(wait=wait, cancel_futures=True)

    @staticmethod
    def _safe_handle(service: MessageService, message: MessagePayload) -> None:
        try:
            service.handle_message(message)
        except Exception as exc:  # noqa: BLE001
            print(f"[services] {service.name} 处理失败: {exc}", flush=True)
