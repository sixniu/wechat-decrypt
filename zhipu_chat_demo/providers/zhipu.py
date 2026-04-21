"""Zhipu AI provider helpers."""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..config.providers import ZHIPU_API_KEY, ZHIPU_MODEL
from ..prompts import TASK_CONFIGS, TaskConfig


class ZhipuRequestError(Exception):
    """Raised when the Zhipu request pipeline fails."""


def create_client() -> Any:
    """Create a Zhipu SDK client.
    """
    try:
        from zai import ZhipuAiClient

        return ZhipuAiClient(api_key=ZHIPU_API_KEY)
    except (ImportError, AttributeError) as exc:  # pragma: no cover - runtime dependency
        raise ZhipuRequestError(
            "未安装可用的智谱 Python SDK，请先执行 `pip install zai-sdk`。"
        ) from exc


def get_task_config(task_type: str) -> TaskConfig:
    """Return the prompt config for a task type."""
    try:
        return TASK_CONFIGS[task_type]
    except KeyError as exc:
        supported = ", ".join(sorted(TASK_CONFIGS))
        raise ZhipuRequestError(
            f"未知提取类型: {task_type}。当前支持: {supported}"
        ) from exc


def build_messages(
    text: str,
    task_type: str,
    *,
    now: dt.datetime | None = None,
) -> list[dict[str, str]]:
    """Build the chat messages for the selected task."""
    if not isinstance(text, str) or not text.strip():
        raise ZhipuRequestError("待提取文本不能为空。")

    config = get_task_config(task_type)
    current_time = now or dt.datetime.now()
    return [
        {"role": "system", "content": config.build_system_prompt(current_time).strip()},
        {"role": "user", "content": text.strip()},
    ]


def request_by_type(text: str, type: str) -> str:
    """Send a typed request to the Zhipu model and return raw text."""
    task_type = type
    messages = build_messages(text, task_type)
    client = create_client()
    response: Any = client.chat.completions.create(
        model=ZHIPU_MODEL,
        messages=messages,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ZhipuRequestError("模型返回空内容，无法继续处理。")
    return content.strip()
