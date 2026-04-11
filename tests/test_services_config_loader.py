import unittest
from unittest.mock import mock_open, patch

from services.config_loader import load_service_config


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


if __name__ == "__main__":
    unittest.main()
