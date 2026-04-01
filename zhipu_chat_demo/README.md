# 智谱基础对话示例

这个目录提供了一个最小可运行的智谱 Python SDK 对话示例，参考官方文档：

- 官方 Python SDK 文档: https://docs.bigmodel.cn/cn/guide/develop/python/introduction

## 文件说明

- `chat_cli.py`: 支持单轮提问和命令行多轮对话

## 使用前需要修改的地方

脚本里默认写了占位 API Key：

```python
DEFAULT_API_KEY = "xxxxxxxxxxxxxxxxxxxx"
```

你可以直接把它改成自己的 Key，或者更推荐设置环境变量 `ZAI_API_KEY`。

## 运行方式

单轮提问：

```bash
python zhipu_chat_demo/chat_cli.py --message "你好，请介绍一下自己"
```

多轮对话：

```bash
python zhipu_chat_demo/chat_cli.py
```

退出命令：

- `quit`
- `exit`
- `q`

## 可选参数

```bash
python zhipu_chat_demo/chat_cli.py --model glm-5 --system-prompt "你是一个专业助手"
```

也可以临时传入 API Key：

```bash
python zhipu_chat_demo/chat_cli.py --api-key "你的真实key" --message "你好"
```

## 说明

- 默认模型使用文档中的 `glm-5`
- 默认是非流式基础对话，便于先快速接通
- 如果后续你想要，我可以继续在这个目录里帮你补上流式输出版、Web 接口版，或者接进你现有项目逻辑
