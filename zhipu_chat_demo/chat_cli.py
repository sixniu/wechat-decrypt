"""Minimal Zhipu AI chat demo based on the official Python SDK docs."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from zai import ZhipuAiClient

DEFAULT_API_KEY = "6e6a4773b82847db9c362798f5450585.FVEQTDd7N6eegatl"
DEFAULT_MODEL = "glm-4.7"
DEFAULT_SYSTEM_PROMPT = "你是一个简洁、友好的 AI 助手。"
EXIT_COMMANDS = {"quit", "exit", "q"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用智谱官方 Python SDK 的基础对话示例。"
    )
    parser.add_argument(
        "-m",
        "--message",
        help="单轮提问内容；不传时进入多轮命令行对话模式。",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"要调用的模型名称，默认值为 {DEFAULT_MODEL}。",
    )
    parser.add_argument(
        "--system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="系统提示词，默认会给助手一个基础角色设定。",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="可选：直接传入 API Key。未传时优先读取环境变量 ZAI_API_KEY，否则使用示例占位值。",
    )
    return parser.parse_args()


def resolve_api_key(cli_api_key: str | None) -> str:
    return cli_api_key or os.getenv("ZAI_API_KEY") or DEFAULT_API_KEY


def create_client(api_key: str) -> ZhipuAiClient:
    return ZhipuAiClient(api_key=api_key)


def build_initial_messages(system_prompt: str) -> list[dict[str, str]]:
    if not system_prompt.strip():
        return []
    return [{"role": "system", "content": system_prompt.strip()}]


def request_completion(
    client: ZhipuAiClient,
    model: str,
    messages: list[dict[str, str]],
) -> str:
    response: Any = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


def run_single_turn(
    client: ZhipuAiClient,
    model: str,
    system_prompt: str,
    message: str,
) -> int:
    messages = build_initial_messages(system_prompt)
    messages.append({"role": "user", "content": message})
    reply = request_completion(client, model, messages)
    print(reply)
    return 0


def run_interactive_chat(
    client: ZhipuAiClient,
    model: str,
    system_prompt: str,
) -> int:
    conversation = build_initial_messages(system_prompt)
    print("智谱基础对话已启动，输入内容开始聊天，输入 quit / exit / q 退出。")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return 0

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("已退出。")
            return 0

        conversation.append({"role": "user", "content": user_input})

        try:
            reply = request_completion(client, model, conversation)
        except Exception as exc:  # noqa: BLE001
            conversation.pop()
            print(f"请求失败: {exc}", file=sys.stderr)
            continue

        print(f"AI: {reply}")
        conversation.append({"role": "assistant", "content": reply})


def main() -> int:
    args = parse_args()
    api_key = resolve_api_key(args.api_key)

    client = create_client(api_key)

    try:
        if args.message:
            return run_single_turn(
                client=client,
                model=args.model,
                system_prompt=args.system_prompt,
                message=args.message,
            )
        return run_interactive_chat(
            client=client,
            model=args.model,
            system_prompt=args.system_prompt,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"程序执行失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
