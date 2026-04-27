import unittest
from unittest.mock import mock_open, patch

from services.config_loader import load_service_config
from services.registry import (
    _build_free_discount_notifier,
    _normalize_chatroom_ids,
    _normalize_sender_ids,
    _normalize_target_chats,
    set_service_wechat_client,
)


class ServiceConfigLoaderTests(unittest.TestCase):
    def test_load_service_config_merges_defaults(self):
        raw = """
        {
            "mysql": {
                "host": "db.example.com",
                "user": "demo"
            },
            "services": {
                "jubensha_booking": {
                    "enabled": true
                }
            }
        }
        """

        with patch("services.config_loader.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=raw)):
                cfg = load_service_config()

        self.assertEqual(cfg["mysql"]["host"], "db.example.com")
        self.assertEqual(cfg["mysql"]["user"], "demo")
        self.assertEqual(cfg["mysql"]["port"], 3306)
        self.assertTrue(cfg["services"]["jubensha_booking"]["enabled"])
        self.assertEqual(cfg["services"]["jubensha_booking"]["provider"], "codex")
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["booking_table"],
            "jubensha_booking",
        )
        self.assertIn(
            "18614995060@chatroom",
            [
                item["id"]
                for item in cfg["services"]["jubensha_booking"][
                    "monitored_chatroom_ids"
                ]
            ],
        )
        self.assertIn(
            "上车",
            cfg["services"]["jubensha_booking"]["trigger_keywords"],
        )
        self.assertIn(
            "wxid_s1rc1q8dj19h22",
            [
                item["id"]
                for item in cfg["services"]["jubensha_booking"][
                    "ignored_sender_ids"
                ]
            ],
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["poster_sender"]["target_chats"],
            ["境由心造"],
        )
        self.assertNotIn(
            "target_chat",
            cfg["services"]["jubensha_booking"]["poster_sender"],
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["poster_sender"]["times"],
            ["10:01", "14:01", "20:01"],
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["allowed_time_range"]["start"],
            "09:30",
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["allowed_time_range"]["end"],
            "20:00",
        )
        self.assertFalse(
            cfg["services"]["jubensha_booking"]["free_discount_notifier"]["enabled"]
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["free_discount_notifier"]["target_chats"],
            [],
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["free_discount_notifier"]["source_chatrooms"],
            [],
        )
        self.assertNotIn(
            "target_chat",
            cfg["services"]["jubensha_booking"]["free_discount_notifier"],
        )
        self.assertFalse(
            cfg["services"]["jubensha_booking"]["free_discount_notice_poller"]["enabled"]
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["free_discount_notice_poller"]["target_chats"],
            [],
        )


class ServiceRegistryConfigTests(unittest.TestCase):
    def test_normalize_chatroom_ids_accepts_named_items_and_legacy_strings(self):
        result = _normalize_chatroom_ids(
            [
                {"id": "18614995060@chatroom", "name": "境由心造"},
                "58262692214@chatroom",
                {"name": "缺少 id"},
            ]
        )

        self.assertEqual(
            result,
            ("18614995060@chatroom", "58262692214@chatroom"),
        )

    def test_normalize_sender_ids_accepts_named_items_and_legacy_strings(self):
        result = _normalize_sender_ids(
            [
                {"id": "wxid_s1rc1q8dj19h22", "name": "自己"},
                "wxid_123",
                {"name": "缺少 id"},
            ]
        )

        self.assertEqual(result, ("wxid_s1rc1q8dj19h22", "wxid_123"))

    def test_normalize_target_chats_accepts_named_items_and_legacy_strings(self):
        result = _normalize_target_chats(
            {
                "target_chats": [
                    {"id": "58262692214@chatroom", "name": "拼好本"},
                    "境由心造",
                    {"id": "47388405090@chatroom"},
                    {"name": "缺少 id 也可按名称发送"},
                ]
            }
        )

        self.assertEqual(
            result,
            ("拼好本", "境由心造", "缺少 id 也可按名称发送"),
        )

    def test_build_free_discount_notifier_reads_source_chatrooms(self):
        wx = object()
        set_service_wechat_client(wx)
        try:
            notifier = _build_free_discount_notifier(
                {
                    "free_discount_notifier": {
                        "enabled": True,
                        "target_chats": [
                            {"id": "58262692214@chatroom", "name": "拼好本"}
                        ],
                        "source_chatrooms": [
                            {"id": "47388405090@chatroom", "name": "剧本杀15群"},
                            "18614995060@chatroom",
                            {"name": "缺少 id"},
                        ],
                        "exact": True,
                    }
                }
            )
        finally:
            set_service_wechat_client(None)

        self.assertIsNotNone(notifier)
        self.assertEqual(notifier._target_chats, ("拼好本",))
        self.assertEqual(
            notifier._source_chatroom_ids,
            ("47388405090@chatroom", "18614995060@chatroom"),
        )


if __name__ == "__main__":
    unittest.main()
