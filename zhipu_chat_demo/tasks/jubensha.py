"""剧本杀任务的后处理层。

这个文件只关注业务校验：
- 把模型返回的原始文本解析成 JSON
- 校验 JSON 结构是否合法
- 校验剧本杀字段是否完整
- 产出标准化后的结构化结果
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from ..config.providers import PROVIDER_ZHIPU
from ..prompts import TASK_JUBENSHA
from ..providers.ai_request import AIRequestError, request_by_type
from .jubensha_constants import JUBENSHA_DISCOUNT_TYPES, JUBENSHA_RESULT_KEYS


class JubenshaExtractionError(Exception):
    """剧本杀提取结果不合法时抛出的异常。"""


def parse_json_array(raw_text: str) -> Any:
    """把模型返回的原始文本解析成 Python 对象。

    参数：
        raw_text: AI 模型返回的原始字符串。

    返回：
        Any: ``json.loads`` 解析后的 Python 对象。

    异常：
        JubenshaExtractionError: 原始文本不是合法 JSON 时抛出。
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JubenshaExtractionError("模型返回的内容不是合法 JSON。") from exc


def _validate_datetime_string(value: str, field_name: str) -> str:
    """校验时间字段是否符合 ``YYYY-MM-DD HH:MM`` 格式。

    参数：
        value: 单条结果中的字段值。
        field_name: 字段名，用于拼接错误信息。

    返回：
        str: 校验通过后的原始时间字符串。

    异常：
        JubenshaExtractionError: 值为空，或者格式不符合要求时抛出。
    """
    if not isinstance(value, str) or not value.strip():
        raise JubenshaExtractionError(f"字段 {field_name} 必须是非空字符串。")
    try:
        dt.datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise JubenshaExtractionError(
            f"字段 {field_name} 格式错误，必须为 YYYY-MM-DD HH:MM。"
        ) from exc
    return value


def _validate_string_field(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool,
) -> str:
    """校验普通字符串字段。

    参数：
        value: 解析后 JSON 里的字段值。
        field_name: 字段名，用于拼接错误信息。
        allow_empty: 是否允许空字符串。

    返回：
        str: 校验通过后的原始字符串。

    异常：
        JubenshaExtractionError: 不是字符串，或者不允许为空但实际为空时抛出。
    """
    if not isinstance(value, str):
        raise JubenshaExtractionError(f"字段 {field_name} 必须是字符串。")
    if not allow_empty and not value.strip():
        raise JubenshaExtractionError(f"字段 {field_name} 不能为空字符串。")
    return value


def validate_jubensha_items(payload: Any) -> list[dict[str, str]]:
    """校验并标准化剧本杀结果列表。

    参数：
        payload: 解析后的 JSON 数据，预期应为对象数组。

    返回：
        list[dict[str, str]]: 校验通过后的剧本杀结果列表，每一项都只保留约定字段。

    异常：
        JubenshaExtractionError: 顶层不是数组、字段缺失、字段值不合法时抛出。
    """
    if not isinstance(payload, list):
        raise JubenshaExtractionError("模型返回的 JSON 顶层必须是数组。")

    validated: list[dict[str, str]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise JubenshaExtractionError(f"第 {index + 1} 条结果必须是对象。")

        missing = [key for key in JUBENSHA_RESULT_KEYS if key not in item]
        if missing:
            missing_text = ", ".join(missing)
            raise JubenshaExtractionError(
                f"第 {index + 1} 条结果缺少字段: {missing_text}"
            )

        discount_type = _validate_string_field(
            item["discount_type"],
            "discount_type",
            allow_empty=False,
        )
        if discount_type not in JUBENSHA_DISCOUNT_TYPES:
            allowed = ", ".join(sorted(JUBENSHA_DISCOUNT_TYPES))
            raise JubenshaExtractionError(
                f"第 {index + 1} 条结果的 discount_type 非法，必须为 {allowed}。"
            )

        validated.append(
            {
                "script_name": _validate_string_field(
                    item["script_name"],
                    "script_name",
                    allow_empty=False,
                ),
                "store_name": _validate_string_field(
                    item["store_name"],
                    "store_name",
                    allow_empty=True,
                ),
                "start_time": _validate_datetime_string(
                    item["start_time"],
                    "start_time",
                ),
                "details": _validate_string_field(
                    item["details"],
                    "details",
                    allow_empty=True,
                ),
                "discount_type": discount_type,
            }
        )
    return validated


def extract_jubensha(text: str, provider: str = PROVIDER_ZHIPU) -> dict[str, Any]:
    """执行完整的剧本杀提取流程。

    参数：
        text: 用户原始文本，例如剧本杀招募、拼车、上车信息等内容。
        provider: AI 提供方标识。默认使用 ``zhipu``，也可以传 ``qwen``。

    返回：
        dict[str, Any]: 最终结果字典，包含：
        - ``type``: 固定为 ``jubensha``
        - ``provider``: 实际使用的 AI 提供方
        - ``data``: 校验后的结构化结果列表
        - ``raw_text``: 模型原始返回文本

    异常：
        JubenshaExtractionError: AI 请求失败、模型返回不是合法 JSON，或者不满足剧本杀结构要求时抛出。
    """
    try:
        raw_text = request_by_type(text, TASK_JUBENSHA, provider=provider)
    except AIRequestError as exc:
        raise JubenshaExtractionError(str(exc)) from exc
    payload = parse_json_array(raw_text)
    data = validate_jubensha_items(payload)
    return {
        "type": TASK_JUBENSHA,
        "provider": provider,
        "data": data,
        "raw_text": raw_text,
    }
