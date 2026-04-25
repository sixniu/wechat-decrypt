import json
import unittest
from unittest.mock import MagicMock

from services.jubensha_booking.free_discount_notice_poller import (
    FreeDiscountNoticePoller,
)


class FreeDiscountNoticePollerTests(unittest.TestCase):
    def test_poll_once_notifies_pending_notice_and_marks_sent(self):
        notifier = MagicMock()
        http_client = _FakeNoticeHttpClient(
            pending_payload={
                "code": 200,
                "data": {
                    "list": [
                        {
                            "id": 7,
                            "payload": {
                                "discount_type": "免单",
                                "script_name": "如故",
                            },
                        }
                    ]
                },
            }
        )
        poller = FreeDiscountNoticePoller(
            api_base_url="https://example.com/api/booking/free-notices",
            token="secret",
            notifier=notifier,
            http_client=http_client,
            limit=5,
        )

        poller.poll_once()

        notifier.notify_if_needed.assert_called_once_with(
            {"discount_type": "免单", "script_name": "如故"}
        )
        self.assertEqual(
            http_client.requests,
            [
                (
                    "GET",
                    "https://example.com/api/booking/free-notices/pending?limit=5",
                    None,
                    "secret",
                ),
                (
                    "POST",
                    "https://example.com/api/booking/free-notices/7/sent",
                    {},
                    "secret",
                ),
            ],
        )

    def test_poll_once_marks_failed_when_notifier_raises(self):
        notifier = MagicMock()
        notifier.notify_if_needed.side_effect = RuntimeError("微信窗口未找到")
        http_client = _FakeNoticeHttpClient(
            pending_payload={
                "code": 200,
                "data": {
                    "list": [
                        {
                            "id": 8,
                            "payload": {
                                "discount_type": "免单",
                                "script_name": "如故",
                            },
                        }
                    ]
                },
            }
        )
        poller = FreeDiscountNoticePoller(
            api_base_url="https://example.com/api/booking/free-notices",
            token="secret",
            notifier=notifier,
            http_client=http_client,
        )

        poller.poll_once()

        self.assertEqual(http_client.requests[-1][0], "POST")
        self.assertEqual(
            http_client.requests[-1][1],
            "https://example.com/api/booking/free-notices/8/failed",
        )
        self.assertEqual(http_client.requests[-1][2], {"message": "微信窗口未找到"})


class _FakeNoticeHttpClient:
    def __init__(self, *, pending_payload):
        self._pending_payload = pending_payload
        self.requests = []

    def get_json(self, url, *, token, timeout):
        self.requests.append(("GET", url, None, token))
        return json.loads(json.dumps(self._pending_payload))

    def post_json(self, url, payload, *, token, timeout):
        self.requests.append(("POST", url, payload, token))
        return {"code": 200, "data": {}}


if __name__ == "__main__":
    unittest.main()
