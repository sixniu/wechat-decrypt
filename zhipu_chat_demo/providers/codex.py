"""本地 Codex 访问层。

这个文件负责：
1. 复用已有业务类型的提示词消息构造。
2. 通过本地 OpenAI 兼容接口请求 Codex 模型。
3. 返回模型的原始文本内容。
"""

from __future__ import annotations

from typing import Any

from ..config.providers import (
    CODEX_API_KEY,
    CODEX_BASE_URL,
    CODEX_MODEL,
)
from .zhipu import build_messages


class CodexRequestError(Exception):
    """Codex 请求阶段的异常。"""


def resolve_api_key() -> str:
    """解析 Codex API Key。"""
    api_key = CODEX_API_KEY
    if api_key.strip():
        return api_key
    raise CodexRequestError("Codex API Key 未配置，请先在 config/providers.py 中填写 CODEX_API_KEY。")


def create_client() -> Any:
    """创建本地 OpenAI 兼容客户端。"""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise CodexRequestError(
            "未安装 openai 包，请先执行 `pip install openai`。"
        ) from exc

    return OpenAI(api_key=resolve_api_key(), base_url=CODEX_BASE_URL)


def request_by_type(text: str, type: str) -> str:
    """按类型请求本地 Codex 模型，并返回原始文本结果。"""
    task_type = type
    messages = build_messages(text, task_type)
    client = create_client()
    try:
        response: Any = client.chat.completions.create(
            model=CODEX_MODEL,
            messages=messages,
        )
        content = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001
        raise CodexRequestError(f"Codex 请求失败: {exc}") from exc

    if not isinstance(content, str) or not content.strip():
        raise CodexRequestError("Codex 返回空内容，无法继续处理。")
    return content.strip()
