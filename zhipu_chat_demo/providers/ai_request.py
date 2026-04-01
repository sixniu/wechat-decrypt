"""统一 AI 请求入口。

外部调用方只需要传入文本、类型和提供方标识，
这个文件会自动分发到对应的 AI 访问层。
"""

from __future__ import annotations

from ..config.providers import PROVIDER_QWEN, PROVIDER_ZHIPU
from .qwen import QwenRequestError, request_by_type as request_qwen_by_type
from .zhipu import ZhipuRequestError, request_by_type as request_zhipu_by_type


class AIRequestError(Exception):
    """统一 AI 请求入口抛出的异常。"""


def request_by_type(text: str, type: str, provider: str = PROVIDER_ZHIPU) -> str:
    """按指定 AI 提供方和业务类型发起请求。

    参数：
        text: 需要发送给模型的原始文本。
        type: 业务类型，例如 ``jubensha``。
        provider: AI 提供方标识。目前支持 ``zhipu`` 和 ``qwen``。

    返回：
        str: 模型返回的原始文本，预期应为 JSON 字符串。

    异常：
        AIRequestError: 提供方未知，或者底层 AI 请求失败时抛出。
    """
    if provider == PROVIDER_ZHIPU:
        try:
            return request_zhipu_by_type(text, type)
        except ZhipuRequestError as exc:
            raise AIRequestError(str(exc)) from exc

    if provider == PROVIDER_QWEN:
        try:
            return request_qwen_by_type(text, type)
        except QwenRequestError as exc:
            raise AIRequestError(str(exc)) from exc

    raise AIRequestError(
        f"未知 AI 提供方: {provider}。当前支持: {PROVIDER_ZHIPU}, {PROVIDER_QWEN}"
    )
