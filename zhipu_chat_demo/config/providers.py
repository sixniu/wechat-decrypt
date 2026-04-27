"""不同 AI 提供方的公共配置。"""

# 可选的 AI 提供方标识。
PROVIDER_ZHIPU = "zhipu"
PROVIDER_QWEN = "qwen"
PROVIDER_CODEX = "codex"

# 智谱访问层使用的内置 API Key。
ZHIPU_API_KEY = "6e6a4773b82847db9c362798f5450585.FVEQTDd7N6eegatl"
# 智谱默认模型名。
ZHIPU_MODEL = "glm-4.7"

# 千问访问层使用的内置 API Key。
QWEN_API_KEY = "sk-8f9d96310e1a46a4bea65f2752787562"
# 千问默认模型名。
QWEN_MODEL = "qwen3.5-plus-2026-02-15"
# 千问兼容 OpenAI SDK 的默认接口根地址。
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 本地 Codex 兼容 OpenAI SDK 的访问配置。
CODEX_API_KEY = "agt_codex_95eHKUjEHxMH52I3ykx3HWljO0H07ZhH"
CODEX_MODEL = "gpt-5.5"
CODEX_BASE_URL = "http://127.0.0.1:53643/v1"
