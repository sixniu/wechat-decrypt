"""不同提取类型的提示词注册表。

这个包只负责维护“类型 -> 系统提示词构造器”的映射关系。
业务校验和模型访问逻辑分别放在其他文件中，避免职责混在一起。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

from .jubensha_prompt import TASK_JUBENSHA, build_jubensha_system_prompt


@dataclass(frozen=True)
class TaskConfig:
    """单个提取类型的系统提示词配置。

    属性说明：
        name: 对外暴露的稳定类型名，例如 ``jubensha``。
        build_system_prompt: 系统提示词构造函数，接收当前时间，返回该类型
            对应的完整系统提示词文本。
    """

    name: str
    build_system_prompt: Callable[[dt.datetime], str]


TASK_CONFIGS: dict[str, TaskConfig] = {
    TASK_JUBENSHA: TaskConfig(
        name=TASK_JUBENSHA,
        build_system_prompt=build_jubensha_system_prompt,
    )
}

__all__ = ["TASK_CONFIGS", "TASK_JUBENSHA", "TaskConfig"]
