"""剧本杀提取结果相关的常量定义。

这个文件只存放剧本杀结构化结果里会重复使用的字段名、枚举值等常量，
避免这些内容散落在校验流程代码中。
"""

# discount_type 字段允许出现的标准枚举值。
JUBENSHA_DISCOUNT_TYPES = {"low_price", "discount", "free", "normal"}

# 每条剧本杀结构化结果必须包含的字段。
JUBENSHA_RESULT_KEYS = (
    "script_name",
    "store_name",
    "start_time",
    "details",
    "discount_type",
)
