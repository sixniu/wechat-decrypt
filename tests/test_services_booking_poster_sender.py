import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.jubensha_booking.poster_sender import (
    BookingPosterError,
    send_booking_poster_to_chat,
    send_booking_poster_to_chats,
    send_poster_to_chat,
)


class BookingPosterSenderTests(unittest.TestCase):
    def test_send_booking_poster_downloads_api_url_and_sends_file(self):
        wx = MagicMock()
        poster_bytes = b"fake-png"
        response = {
            "code": 200,
            "msg": "ok",
            "data": {
                "url": "https://www.shisan.ink/storage/posters/booking/demo.png",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("services.jubensha_booking.poster_sender.urlopen") as mocked_urlopen:
                mocked_urlopen.side_effect = [
                    _FakeResponse(json.dumps(response).encode("utf-8")),
                    _FakeResponse(poster_bytes),
                ]

                saved_path = send_booking_poster_to_chat(
                    who="测试群",
                    wx=wx,
                    exact=True,
                    download_dir=temp_dir,
                    api_url="https://www.shisan.ink/api/booking/poster",
                )

        self.assertEqual(Path(saved_path).name, "demo.png")
        wx.SendFiles.assert_called_once_with(
            filepath=saved_path,
            who="测试群",
            exact=True,
        )

    def test_send_booking_poster_raises_when_api_has_no_url(self):
        wx = MagicMock()
        response = {"code": 200, "msg": "ok", "data": {}}

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("services.jubensha_booking.poster_sender.urlopen") as mocked_urlopen:
                mocked_urlopen.return_value = _FakeResponse(
                    json.dumps(response).encode("utf-8")
                )

                with self.assertRaises(BookingPosterError) as ctx:
                    send_booking_poster_to_chat(
                        who="测试群",
                        wx=wx,
                        download_dir=temp_dir,
                    )

        self.assertIn("url", str(ctx.exception))
        wx.SendFiles.assert_not_called()

    def test_send_booking_poster_requires_initialized_wechat_client(self):
        with self.assertRaises(BookingPosterError) as ctx:
            send_booking_poster_to_chat(who="测试群")

        self.assertIn("wx", str(ctx.exception))

    def test_send_booking_poster_to_chats_downloads_once_and_sends_many_times(self):
        wx = MagicMock()
        poster_bytes = b"fake-png"
        response = {
            "code": 200,
            "msg": "ok",
            "data": {
                "url": "https://www.shisan.ink/storage/posters/booking/demo.png",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("services.jubensha_booking.poster_sender.urlopen") as mocked_urlopen:
                mocked_urlopen.side_effect = [
                    _FakeResponse(json.dumps(response).encode("utf-8")),
                    _FakeResponse(poster_bytes),
                ]

                saved_path = send_booking_poster_to_chats(
                    who_list=["群A", "群B"],
                    wx=wx,
                    exact=True,
                    download_dir=temp_dir,
                    api_url="https://www.shisan.ink/api/booking/poster",
                )

        self.assertEqual(Path(saved_path).name, "demo.png")
        self.assertEqual(wx.SendFiles.call_count, 2)
        wx.SendFiles.assert_any_call(filepath=saved_path, who="群A", exact=True)
        wx.SendFiles.assert_any_call(filepath=saved_path, who="群B", exact=True)

    def test_send_poster_to_chat_delegates_to_wechat_client_send_file(self):
        wx = MagicMock()

        with patch("services.jubensha_booking.poster_sender.send_file") as mocked_send_file:
            result = send_poster_to_chat(
                "C:/posters/demo.png",
                who="测试群",
                wx=wx,
                exact=True,
            )

        self.assertEqual(result, "C:/posters/demo.png")
        mocked_send_file.assert_called_once_with(
            wx=wx,
            filepath="C:/posters/demo.png",
            who="测试群",
            exact=True,
        )


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


if __name__ == "__main__":
    unittest.main()
