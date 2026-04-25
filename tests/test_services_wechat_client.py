import unittest
from unittest.mock import MagicMock

from services.wechat_client import (
    WechatClientError,
    at_all,
    send_file,
    send_text,
)


class WechatClientTests(unittest.TestCase):
    def test_wechat_helpers_are_exported_from_services_package(self):
        import services

        self.assertIs(services.send_file, send_file)
        self.assertIs(services.send_text, send_text)
        self.assertIs(services.at_all, at_all)

    def test_send_file_calls_wxautox_send_files(self):
        wx = MagicMock()

        result = send_file(
            wx=wx,
            filepath="C:/文件.txt",
            who="张三",
            exact=True,
        )

        wx.SendFiles.assert_called_once_with(
            filepath="C:/文件.txt",
            who="张三",
            exact=True,
        )
        self.assertIs(result, wx.SendFiles.return_value)

    def test_send_text_calls_wxautox_send_msg(self):
        wx = MagicMock()

        result = send_text(
            wx=wx,
            msg="你好",
            who="张三",
            clear=False,
            at="李四",
            exact=True,
        )

        wx.SendMsg.assert_called_once_with(
            msg="你好",
            who="张三",
            clear=False,
            at="李四",
            exact=True,
        )
        self.assertIs(result, wx.SendMsg.return_value)

    def test_at_all_calls_wxautox_at_all(self):
        wx = MagicMock()

        result = at_all(
            wx=wx,
            msg="通知",
            who="工作群",
            exact=True,
        )

        wx.AtAll.assert_called_once_with("通知", "工作群", exact=True)
        self.assertIs(result, wx.AtAll.return_value)

    def test_send_file_requires_initialized_wechat_client(self):
        with self.assertRaises(WechatClientError) as ctx:
            send_file(wx=None, filepath="C:/文件.txt", who="张三")

        self.assertIn("wx", str(ctx.exception))

    def test_send_text_requires_message_content(self):
        wx = MagicMock()

        with self.assertRaises(WechatClientError) as ctx:
            send_text(wx=wx, msg="", who="张三")

        self.assertIn("消息内容", str(ctx.exception))
        wx.SendMsg.assert_not_called()


if __name__ == "__main__":
    unittest.main()
