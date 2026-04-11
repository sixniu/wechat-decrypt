"""服务目录自己的配置加载器。"""

from __future__ import annotations

import json
import os
from typing import Any

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_CONFIG_FILE = os.path.join(SERVICE_DIR, "config.json")
SERVICE_CONFIG_EXAMPLE_FILE = os.path.join(SERVICE_DIR, "config.example.json")

DEFAULT_SERVICE_CONFIG: dict[str, Any] = {
    "mysql": {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "",
        "password": "",
        "database": "",
        "charset": "utf8mb4",
    },
    "services": {
        "jubensha_booking": {
            "enabled": False,
            "provider": "zhipu",
            "raw_table": "jubensha_all_content",
            "booking_table": "jubensha_booking",
        }
    },
}


def load_service_config() -> dict[str, Any]:
    """读取 services 目录自己的配置。"""
    cfg: dict[str, Any] = {}
    if os.path.exists(SERVICE_CONFIG_FILE):
        try:
            with open(SERVICE_CONFIG_FILE, encoding="utf-8") as file:
                cfg = json.load(file)
        except json.JSONDecodeError:
            print(
                f"[services] 配置文件格式错误: {SERVICE_CONFIG_FILE}",
                flush=True,
            )
            cfg = {}
    return _deep_merge(DEFAULT_SERVICE_CONFIG, cfg)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
