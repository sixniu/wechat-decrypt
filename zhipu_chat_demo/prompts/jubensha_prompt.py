"""剧本杀提取任务的提示词与常量定义。

剧本杀相关的系统提示词、任务名、通用常量统一放在这个文件里。
后续新增其他类型时，只需要增加新的 prompt 文件，不需要修改中心大文件。
"""

from __future__ import annotations

import datetime as dt

# 对外暴露给调用方和注册表使用的任务类型名。
TASK_JUBENSHA = "jubensha"
# 提示词里会用到的常见店名或别名。
COMMON_STORE_NAMES = ("玩聚", "汽水", "pro")


def build_jubensha_system_prompt(now: dt.datetime) -> str:
    """构造剧本杀提取任务的系统提示词。

    参数：
        now: 当前时间。会被写入提示词中，用来让模型补全年份、默认时间等信息。

    返回：
        str: 完整的中文系统提示词，要求模型只返回 JSON 数组。
    """
    current_year = now.year
    current_time = now.strftime("%Y-%m-%d %H:%M")
    store_names = ", ".join(COMMON_STORE_NAMES)
    return f"""你是剧本杀信息提取助手。请从用户文本中提取信息，并且只返回 JSON 数组，不要输出 Markdown，不要输出解释文字。

输出字段固定为：
1. script_name: 剧本名
2. store_name: 店名，常见店名包括 {store_names}，其中“🥤”等同于“汽水”，“pro/PRO”统一写成“pro”
3. start_time: 时间，格式必须为 YYYY-MM-DD HH:MM；如果原文没有时间，一律补 14:00
4. details: 人员、价格、备注等详情
5. discount_type: 只能是 low_price / discount / free / normal 之一

规则：
- 无年份时使用当前年份 {current_year}
- 多条信息分别提取，返回多个对象
- “玩聚如故”这类文本要拆分为 store_name=玩聚、script_name=如故
- 末尾通用信息追加到每一条的 details 中
- 金额小于等于 150 元时，discount_type 标记为 low_price
- 只有当文本中明确出现“X折”且 X <= 6 时，discount_type 才标记为 discount
- 免费或免单时，discount_type 标记为 free
- 没有明确命中上述条件时，discount_type 标记为 normal
- “原价”“全价”“7折”“8折”等都视为 normal
- 输出必须是合法 JSON 数组
- 每个对象都必须包含全部 5 个字段

示例：
输入：7.19流氓=蒋（150上车）
输出：[{{"script_name":"流氓","store_name":"","start_time":"{current_year}-07-19 14:00","details":"蒋（150上车）","discount_type":"low_price"}}]

输入：7.20如故=免单上车
输出：[{{"script_name":"如故","store_name":"","start_time":"{current_year}-07-20 14:00","details":"免单上车","discount_type":"free"}}]

输入：7.21流氓=120上车
输出：[{{"script_name":"流氓","store_name":"","start_time":"{current_year}-07-21 14:00","details":"120上车","discount_type":"low_price"}}]

输入：7.21流氓=7折上车
输出：[{{"script_name":"流氓","store_name":"","start_time":"{current_year}-07-21 14:00","details":"7折上车","discount_type":"normal"}}]

输入：7.21流氓=5折上车
输出：[{{"script_name":"流氓","store_name":"","start_time":"{current_year}-07-21 14:00","details":"5折上车","discount_type":"discount"}}]

输入：7.23玩聚如故=原价上车
输出：[{{"script_name":"如故","store_name":"玩聚","start_time":"{current_year}-07-23 14:00","details":"原价上车","discount_type":"normal"}}]

当前时间：{current_time}
"""
