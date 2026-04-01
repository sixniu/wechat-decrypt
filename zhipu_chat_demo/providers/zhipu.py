"""智谱访问层。

这个文件只负责三件事：
1. 根据类型名找到对应的系统提示词配置。
2. 组装发送给智谱模型的消息列表。
3. 发起请求并返回模型的原始文本结果。
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..config.providers import ZHIPU_API_KEY, ZHIPU_MODEL
from ..prompts import TASK_CONFIGS, TaskConfig


class ZhipuRequestError(Exception):
    """智谱请求阶段的异常。"""


def create_client() -> Any:
    """创建智谱 SDK 客户端。

    返回：
        Any: 初始化完成的 ``ZhipuAiClient`` 实例。

    异常：
        ZhipuRequestError: 当前环境未安装智谱 SDK 时抛出。
    """
    try:
        from zai import ZhipuAiClient
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise ZhipuRequestError(
            "未安装智谱 Python SDK，请先执行 `pip install zai`。"
        ) from exc
    return ZhipuAiClient(api_key=ZHIPU_API_KEY)


def get_task_config(task_type: str) -> TaskConfig:
    """根据类型名获取对应的提示词配置。

    参数：
        task_type: 调用方传入的提取类型，例如 ``jubensha``。

    返回：
        TaskConfig: 该类型对应的提示词配置对象。

    异常：
        ZhipuRequestError: 类型未注册时抛出。
    """
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
    """构造一次类型化提取请求的消息列表。

    参数：
        text: 待提取的原始文本。
        task_type: 提取类型，用来选择对应的系统提示词。
        now: 可选的当前时间。测试时可以传固定值，让提示词结果稳定。

    返回：
        list[dict[str, str]]: 发送给智谱模型的消息列表，固定包含 system 和 user
        两条消息。

    异常：
        ZhipuRequestError: 文本为空，或者类型不存在时抛出。
    """
    if not isinstance(text, str) or not text.strip():
        raise ZhipuRequestError("待提取文本不能为空。")

    config = get_task_config(task_type)
    current_time = now or dt.datetime.now()
    return [
        {"role": "system", "content": config.build_system_prompt(current_time).strip()},
        {"role": "user", "content": text.strip()},
    ]


def request_by_type(text: str, type: str) -> str:
    """按类型请求智谱模型，并返回原始文本结果。

    参数：
        text: 需要发送给模型的原始文本。
        type: 提取类型。目前支持 ``jubensha``。

    返回：
        str: 模型返回的原始文本，预期应为 JSON 字符串。

    异常：
        ZhipuRequestError: 类型无效、SDK 调用失败，或者模型返回空内容时抛出。
    """
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
