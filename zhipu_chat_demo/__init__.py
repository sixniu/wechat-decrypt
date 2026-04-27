"""模块公共导出入口。

外部代码如果只关心稳定的公共接口，而不关心内部文件如何拆分，
直接从这个包导入即可。
"""

from .config.providers import PROVIDER_CODEX, PROVIDER_QWEN, PROVIDER_ZHIPU
from .prompts import TASK_JUBENSHA
from .providers import (
    AIRequestError,
    CodexRequestError,
    QwenRequestError,
    ZhipuRequestError,
    request_by_type,
)
from .tasks import (
    JUBENSHA_DISCOUNT_TYPES,
    JUBENSHA_RESULT_KEYS,
    JubenshaExtractionError,
    extract_jubensha,
)

__all__ = [
    "AIRequestError",
    "CodexRequestError",
    "JUBENSHA_DISCOUNT_TYPES",
    "JUBENSHA_RESULT_KEYS",
    "PROVIDER_CODEX",
    "PROVIDER_QWEN",
    "PROVIDER_ZHIPU",
    "TASK_JUBENSHA",
    "QwenRequestError",
    "ZhipuRequestError",
    "JubenshaExtractionError",
    "request_by_type",
    "extract_jubensha",
]
