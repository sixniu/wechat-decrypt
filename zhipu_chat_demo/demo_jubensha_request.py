"""剧本杀提取调用示例。

这个示例文件演示外部代码如何直接调用 ``extract_jubensha``，
把一段原始文本提取成结构化结果。
"""

from __future__ import annotations

import json

from zhipu_chat_demo import PROVIDER_ZHIPU, extract_jubensha
from zhipu_chat_demo.config.providers import PROVIDER_CODEX


def main() -> None:
    """执行一次剧本杀提取示例并打印结果。"""
    text = "顾飞雪 7.23玩聚如故=原价上车，微信 gf123456"
    result = extract_jubensha(text, provider=PROVIDER_CODEX)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
