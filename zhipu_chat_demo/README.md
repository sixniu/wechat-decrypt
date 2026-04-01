# AI 剧本杀提取模块

这个小模块现在拆成了三层：

- `providers/ai_request.py`
  统一入口，外部可以选择调用哪一个 AI 提供方
- `providers/zhipu.py` / `providers/qwen.py`
  分别负责各自 AI 提供方的具体请求实现
- `tasks/jubensha.py`
  只负责处理剧本杀返回值，判断是不是合法 JSON，并组装成最终结果

现在和“类型定义”相关的内容也继续拆开了，后面加其他需求不会都堆在一个文件里。

## 文件结构

- `config/providers.py`: 不同 AI 提供方的模型名、接口地址、内置 key
- `prompts/jubensha_prompt.py`: 剧本杀相关的系统提示词、常量、任务名
- `prompts/__init__.py`: 类型注册表
- `tasks/jubensha_constants.py`: 剧本杀结果字段名、枚举值等公共常量
- `providers/zhipu.py`: 智谱访问层
- `providers/qwen.py`: 千问访问层
- `providers/ai_request.py`: 统一 AI 请求入口，对外开放 `request_by_type(text, type, provider)`
- `tasks/jubensha.py`: 剧本杀处理层，对外开放 `extract_jubensha(text, provider=...)`

## 安装依赖

```bash
pip install -r zhipu_chat_demo/requirements.txt
```

## 直接访问 AI

如果你只想传入文本、类型和 AI 提供方，让模型按对应提示词返回原始文本：

```python
from zhipu_chat_demo import PROVIDER_ZHIPU, request_by_type

raw_text = request_by_type("7.23玩聚如故=原价上车", "jubensha", provider=PROVIDER_ZHIPU)
print(raw_text)
```

## 剧本杀结构化提取

如果你想直接拿到处理好的 JSON 结构：

```python
from zhipu_chat_demo import PROVIDER_QWEN, extract_jubensha

result = extract_jubensha("7.23玩聚如故=原价上车", provider=PROVIDER_QWEN)
print(result["data"])
```

也可以直接运行示例文件：

```bash
python -m zhipu_chat_demo.demo_jubensha_request
```

返回结构：

```json
{
  "type": "jubensha",
  "provider": "qwen",
  "data": [
    {
      "script_name": "如故",
      "store_name": "玩聚",
      "start_time": "2026-07-23 14:00",
      "details": "原价上车",
      "discount_type": "normal"
    }
  ],
  "raw_text": "[...]"
}
```

## 说明

- 模型名、接口地址和内置 key 已配置在 `config/providers.py`
- 千问支持百炼官方兼容 OpenAI SDK 的调用方式
- 千问和智谱一样，直接读取 `config/providers.py` 里的内置 key
- 现在支持两种 AI 提供方：
  - `zhipu`
  - `qwen`
- 目前只内置了 `jubensha` 这一种类型
- 后面如果增加新类型，建议新增一个 `prompts/xxx_prompt.py` 和一个 `xxx.py`
- 当前目录已经按最新结构使用，不保留旧兼容入口
- 剧本杀处理层会严格校验：
  - 返回值必须是合法 JSON
  - 顶层必须是数组
  - 每条数据必须包含完整字段
  - `discount_type` 只能是 `low_price / discount / free / normal`
