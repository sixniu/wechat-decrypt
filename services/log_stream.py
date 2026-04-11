"""服务日志事件流。"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

MAX_SERVICE_LOGS = 500

_service_logs: list[dict[str, Any]] = []
_service_logs_lock = threading.Lock()
_log_sink: Callable[[dict[str, Any]], None] | None = None


def emit_service_log(
    *,
    service: str,
    trace_id: str,
    message: str,
    kind: str = "log",
    data: Any = None,
) -> dict[str, Any]:
    """记录一条服务日志，并推送给外部观察器。"""
    payload = {
        "service": service,
        "trace_id": trace_id,
        "message": message,
        "kind": kind,
        "data": data,
        "timestamp_ms": int(time.time() * 1000),
        "time": time.strftime("%H:%M:%S"),
    }
    with _service_logs_lock:
        _service_logs.append(payload)
        if len(_service_logs) > MAX_SERVICE_LOGS:
            del _service_logs[:-MAX_SERVICE_LOGS]

    sink = _log_sink
    if sink:
        try:
            sink(dict(payload))
        except Exception as exc:  # noqa: BLE001
            print(f"[services] service_log sink 失败: {exc}", flush=True)
    return payload


def get_service_log_history() -> list[dict[str, Any]]:
    """返回服务日志历史。"""
    with _service_logs_lock:
        return list(_service_logs)


def set_service_log_sink(sink: Callable[[dict[str, Any]], None] | None) -> None:
    """设置服务日志外部推送器。"""
    global _log_sink
    _log_sink = sink
