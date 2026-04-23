import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import main as app_main


class MainWebNewTests(unittest.TestCase):
    def test_web_new_initializes_wechat_once_and_passes_to_monitor(self):
        wx_instance = MagicMock()
        fake_wxautox4 = types.SimpleNamespace(WeChat=MagicMock(return_value=wx_instance))
        fake_monitor = types.SimpleNamespace(main=MagicMock())
        fake_config = types.SimpleNamespace(
            load_config=MagicMock(
                return_value={
                    "keys_file": "keys.json",
                    "db_dir": "db",
                    "wechat_process": "WeChat",
                }
            )
        )

        modules = {
            "wxautox4": fake_wxautox4,
            "monitor_web_new": fake_monitor,
            "config": fake_config,
        }

        with patch.dict(sys.modules, modules):
            with patch.object(sys, "argv", ["main.py", "web_new"]):
                with patch.object(app_main, "check_wechat_running", return_value=True):
                    with patch.object(app_main, "ensure_keys"):
                        app_main.main()

        fake_wxautox4.WeChat.assert_called_once_with("人类群星闪耀时")
        fake_monitor.main.assert_called_once_with(wx=wx_instance)


if __name__ == "__main__":
    unittest.main()
