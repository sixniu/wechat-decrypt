import datetime as dt
import json
import unittest
from unittest.mock import patch

from zhipu_chat_demo.providers import ai_request, qwen, zhipu
from zhipu_chat_demo.tasks import jubensha
from zhipu_chat_demo.tasks.jubensha_constants import (
    JUBENSHA_DISCOUNT_TYPES,
    JUBENSHA_RESULT_KEYS,
)
from zhipu_chat_demo.config.providers import (
    PROVIDER_QWEN,
    PROVIDER_ZHIPU,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
    ZHIPU_MODEL,
)
from zhipu_chat_demo.prompts import TASK_JUBENSHA
from zhipu_chat_demo.prompts.jubensha_prompt import COMMON_STORE_NAMES


class ZhipuAiLayerTests(unittest.TestCase):
    def test_build_messages_uses_type_registry_prompt(self):
        fixed_now = dt.datetime(2026, 4, 1, 20, 30)

        messages = zhipu.build_messages(
            "7.21流氓=120上车",
            TASK_JUBENSHA,
            now=fixed_now,
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("剧本杀信息提取助手", messages[0]["content"])
        self.assertIn("当前年份 2026", messages[0]["content"])
        self.assertIn(", ".join(COMMON_STORE_NAMES), messages[0]["content"])
        self.assertEqual(messages[1], {"role": "user", "content": "7.21流氓=120上车"})

    def test_request_by_type_rejects_unknown_type(self):
        with self.assertRaisesRegex(zhipu.ZhipuRequestError, "未知提取类型"):
            zhipu.request_by_type("hello", "unknown")

    def test_request_by_type_uses_built_in_model(self):
        calls = []
        fake_response = type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": "[]"})()},
                    )()
                ]
            },
        )()
        fake_client = type(
            "Client",
            (),
            {
                "chat": type(
                    "Chat",
                    (),
                    {
                        "completions": type(
                            "Completions",
                            (),
                            {
                                "create": lambda self, **kwargs: (
                                    calls.append(kwargs) or fake_response
                                )
                            },
                        )()
                    },
                )()
            },
        )()

        with patch.object(zhipu, "create_client", return_value=fake_client):
            content = zhipu.request_by_type("7.21流氓=120上车", TASK_JUBENSHA)

        self.assertEqual(content, "[]")
        self.assertEqual(calls[0]["model"], ZHIPU_MODEL)

    def test_request_by_type_rejects_empty_content(self):
        fake_response = type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": "   "})()},
                    )()
                ]
            },
        )()
        fake_client = type(
            "Client",
            (),
            {
                "chat": type(
                    "Chat",
                    (),
                    {
                        "completions": type(
                            "Completions",
                            (),
                            {"create": lambda self, **kwargs: fake_response},
                        )()
                    },
                )()
            },
        )()

        with patch.object(zhipu, "create_client", return_value=fake_client):
            with self.assertRaisesRegex(zhipu.ZhipuRequestError, "模型返回空内容"):
                zhipu.request_by_type("7.21流氓=120上车", "jubensha")


class JubenshaLayerTests(unittest.TestCase):
    def test_extract_jubensha_returns_structured_result(self):
        raw_text = json.dumps(
            [
                {
                    "script_name": "如故",
                    "store_name": "玩聚",
                    "start_time": "2026-07-23 14:00",
                    "details": "原价上车",
                    "discount_type": "normal",
                }
            ],
            ensure_ascii=False,
        )

        with patch.object(jubensha, "request_by_type", return_value=raw_text):
            result = jubensha.extract_jubensha("7.23玩聚如故=原价上车")

        self.assertEqual(result["type"], "jubensha")
        self.assertEqual(result["provider"], PROVIDER_ZHIPU)
        self.assertEqual(result["raw_text"], raw_text)
        self.assertEqual(result["data"][0]["script_name"], "如故")
        self.assertEqual(result["data"][0]["store_name"], "玩聚")

    def test_extract_jubensha_supports_provider_argument(self):
        raw_text = json.dumps(
            [
                {
                    "script_name": "如故",
                    "store_name": "玩聚",
                    "start_time": "2026-07-23 14:00",
                    "details": "原价上车",
                    "discount_type": "normal",
                }
            ],
            ensure_ascii=False,
        )

        with patch.object(jubensha, "request_by_type", return_value=raw_text) as mocked:
            result = jubensha.extract_jubensha(
                "7.23玩聚如故=原价上车",
                provider=PROVIDER_QWEN,
            )

        mocked.assert_called_once_with("7.23玩聚如故=原价上车", TASK_JUBENSHA, provider=PROVIDER_QWEN)
        self.assertEqual(result["provider"], PROVIDER_QWEN)

    def test_extract_jubensha_rejects_invalid_json(self):
        with patch.object(jubensha, "request_by_type", return_value="not json"):
            with self.assertRaisesRegex(jubensha.JubenshaExtractionError, "不是合法 JSON"):
                jubensha.extract_jubensha("7.21流氓=120上车")

    def test_validate_jubensha_supports_multiple_entries(self):
        payload = [
            {
                "script_name": "流氓",
                "store_name": "",
                "start_time": "2026-07-21 14:00",
                "details": "120上车",
                "discount_type": "low_price",
            },
            {
                "script_name": "如故",
                "store_name": "玩聚",
                "start_time": "2026-07-23 14:00",
                "details": "原价上车",
                "discount_type": "normal",
            },
        ]

        self.assertEqual(jubensha.validate_jubensha_items(payload), payload)
        self.assertIn("normal", JUBENSHA_DISCOUNT_TYPES)
        self.assertEqual(JUBENSHA_RESULT_KEYS[0], "script_name")

    def test_validate_jubensha_rejects_invalid_discount_values(self):
        payload = [
            {
                "script_name": "流氓",
                "store_name": "",
                "start_time": "2026-07-21 14:00",
                "details": "7折上车",
                "discount_type": "折扣",
            }
        ]

        with self.assertRaisesRegex(
            jubensha.JubenshaExtractionError,
            "discount_type 非法",
        ):
            jubensha.validate_jubensha_items(payload)

    def test_validate_jubensha_rejects_invalid_datetime(self):
        payload = [
            {
                "script_name": "流氓",
                "store_name": "",
                "start_time": "2026/07/21",
                "details": "120上车",
                "discount_type": "low_price",
            }
        ]

        with self.assertRaisesRegex(
            jubensha.JubenshaExtractionError,
            "YYYY-MM-DD HH:MM",
        ):
            jubensha.validate_jubensha_items(payload)


class AIRequestLayerTests(unittest.TestCase):
    def test_request_by_type_routes_to_zhipu(self):
        with patch.object(ai_request, "request_zhipu_by_type", return_value="[]") as mocked:
            result = ai_request.request_by_type("文本", TASK_JUBENSHA, provider=PROVIDER_ZHIPU)

        mocked.assert_called_once_with("文本", TASK_JUBENSHA)
        self.assertEqual(result, "[]")

    def test_request_by_type_routes_to_qwen(self):
        with patch.object(ai_request, "request_qwen_by_type", return_value="[]") as mocked:
            result = ai_request.request_by_type("文本", TASK_JUBENSHA, provider=PROVIDER_QWEN)

        mocked.assert_called_once_with("文本", TASK_JUBENSHA)
        self.assertEqual(result, "[]")

    def test_request_by_type_rejects_unknown_provider(self):
        with self.assertRaisesRegex(ai_request.AIRequestError, "未知 AI 提供方"):
            ai_request.request_by_type("文本", TASK_JUBENSHA, provider="unknown")


class QwenLayerTests(unittest.TestCase):
    def test_qwen_requires_api_key(self):
        with patch.object(qwen, "QWEN_API_KEY", ""):
            with self.assertRaisesRegex(qwen.QwenRequestError, "千问 API Key 未配置"):
                qwen.resolve_api_key()

    def test_qwen_resolve_api_key_reads_builtin_config(self):
        with patch.object(qwen, "QWEN_API_KEY", "config-key"):
            self.assertEqual(qwen.resolve_api_key(), "config-key")

    def test_qwen_create_client_uses_openai_compatible_settings(self):
        calls = []

        class FakeOpenAI:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        with patch.object(qwen, "QWEN_API_KEY", "config-key"):
            with patch("openai.OpenAI", FakeOpenAI):
                qwen.create_client()

        self.assertEqual(calls[0]["api_key"], "config-key")
        self.assertEqual(calls[0]["base_url"], QWEN_BASE_URL)

    def test_qwen_request_by_type_uses_openai_client(self):
        calls = []
        fake_response = type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": "[]"})()},
                    )()
                ]
            },
        )()
        fake_client = type(
            "Client",
            (),
            {
                "chat": type(
                    "Chat",
                    (),
                    {
                        "completions": type(
                            "Completions",
                            (),
                            {
                                "create": lambda self, **kwargs: (
                                    calls.append(kwargs) or fake_response
                                )
                            },
                        )()
                    },
                )()
            },
        )()

        with patch.object(qwen, "create_client", return_value=fake_client):
            content = qwen.request_by_type("文本", TASK_JUBENSHA)

        self.assertEqual(content, "[]")
        self.assertEqual(calls[0]["model"], QWEN_MODEL)


if __name__ == "__main__":
    unittest.main()
