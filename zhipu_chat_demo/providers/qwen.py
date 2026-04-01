"""千问访问层。

这个文件负责：
1. 根据类型名找到对应的系统提示词配置。
2. 组装发送给千问模型的消息列表。
3. 通过百炼兼容 OpenAI SDK 的方式返回原始文本结果。
"""

from __future__ import annotations

from typing import Any

from ..config.providers import (
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
)
from .zhipu import build_messages


class QwenRequestError(Exception):
    """千问请求阶段的异常。"""


def resolve_api_key() -> str:
    """解析千问 API Key。

    返回：
        str: 实际可用的千问 API Key，直接从内置配置中读取。

    异常：
        QwenRequestError: 未配置内置密钥时抛出。
    """
    api_key = QWEN_API_KEY
    if api_key.strip():
        return api_key
    raise QwenRequestError("千问 API Key 未配置，请先在 config/providers.py 中填写 QWEN_API_KEY。")


def create_client() -> Any:
    """创建千问 OpenAI 兼容客户端。

    返回：
        Any: 初始化完成的 OpenAI 客户端实例。

    异常：
        QwenRequestError: 当前环境未安装 openai 包，或者未配置有效 API Key 时抛出。
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise QwenRequestError(
            "未安装 openai 包，请先执行 `pip install openai`。"
        ) from exc

    return OpenAI(api_key=resolve_api_key(), base_url=QWEN_BASE_URL)


def request_by_type(text: str, type: str) -> str:
    """按类型请求千问模型，并返回原始文本结果。

    参数：
        text: 需要发送给模型的原始文本。
        type: 提取类型。目前支持 ``jubensha``。

    返回：
        str: 模型返回的原始文本，预期应为 JSON 字符串。

    异常：
        QwenRequestError: 类型无效、未配置密钥、SDK 调用失败，或者模型返回空内容时抛出。
    """
    task_type = type
    messages = build_messages(text, task_type)
    client = create_client()
    try:
        response: Any = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=messages,
        )
        content = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001
        raise QwenRequestError(f"千问请求失败: {exc}") from exc

    if not isinstance(content, str) or not content.strip():
        raise QwenRequestError("千问返回空内容，无法继续处理。")
    return content.strip()
