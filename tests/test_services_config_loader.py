import unittest
from unittest.mock import mock_open, patch

from services.config_loader import load_service_config
from services.registry import _normalize_chatroom_ids


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
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["poster_sender"]["target_chat"],
            "境由心造",
        )
        self.assertEqual(
            cfg["services"]["jubensha_booking"]["poster_sender"]["target_chats"],
            ["境由心造"],
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


if __name__ == "__main__":
    unittest.main()
