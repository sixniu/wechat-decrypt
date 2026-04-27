import unittest
from unittest.mock import MagicMock, patch

from services.jubensha_booking.free_discount_notifier import FreeDiscountNotifier


class FreeDiscountNotifierTests(unittest.TestCase):
    def test_notify_if_needed_mentions_all_for_free_discount(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(
            wx=wx,
            target_chats=("境由心造",),
            exact=True,
        )
        booking_item = {
            "booking_time": "2026-07-23 14:00",
            "store_name": "玩聚",
            "script_name": "如故",
            "script_details": "免单上车",
            "discount_type": "免单",
            "user_name": "顾飞雪",
        }

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(booking_item)

        mocked_at_all.assert_called_once()
        kwargs = mocked_at_all.call_args.kwargs
        self.assertIs(kwargs["wx"], wx)
        self.assertEqual(kwargs["who"], "境由心造")
        self.assertTrue(kwargs["exact"])
        self.assertIn("免单", kwargs["msg"])
        self.assertIn("如故", kwargs["msg"])

    def test_notify_if_needed_mentions_all_when_source_chatroom_is_allowed(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(
            wx=wx,
            target_chats=("通知群",),
            source_chatroom_ids=("47388405090@chatroom",),
            exact=True,
        )

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(
                {
                    "discount_type": "免单",
                    "script_name": "如故",
                    "booking_time": "2026-07-23 14:00",
                },
                source_chatroom_id="47388405090@chatroom",
            )

        mocked_at_all.assert_called_once()
        self.assertEqual(mocked_at_all.call_args.kwargs["who"], "通知群")

    def test_notify_if_needed_skips_when_source_chatroom_is_not_allowed(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(
            wx=wx,
            target_chats=("通知群",),
            source_chatroom_ids=("47388405090@chatroom",),
        )

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(
                {
                    "discount_type": "免单",
                    "script_name": "如故",
                    "booking_time": "2026-07-23 14:00",
                },
                source_chatroom_id="18614995060@chatroom",
            )

        mocked_at_all.assert_not_called()

    def test_notify_if_needed_skips_non_free_discount(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(wx=wx)

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(
                {
                    "discount_type": "正常",
                    "script_name": "如故",
                }
            )

        mocked_at_all.assert_not_called()

    def test_notify_if_needed_uses_configured_target_chats_first(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(
            wx=wx,
            target_chats=("通知群A", "通知群B"),
            exact=False,
        )

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(
                {
                    "discount_type": "免单",
                    "script_name": "如故",
                    "booking_time": "2026-07-23 14:00",
                }
            )

        self.assertEqual(mocked_at_all.call_count, 2)
        mocked_at_all.assert_any_call(
            wx=wx,
            msg=mocked_at_all.call_args_list[0].kwargs["msg"],
            who="通知群A",
            exact=False,
        )
        mocked_at_all.assert_any_call(
            wx=wx,
            msg=mocked_at_all.call_args_list[1].kwargs["msg"],
            who="通知群B",
            exact=False,
        )

    def test_notify_if_needed_skips_when_target_chats_is_empty(self):
        wx = MagicMock()
        notifier = FreeDiscountNotifier(wx=wx)

        with patch("services.jubensha_booking.free_discount_notifier.at_all") as mocked_at_all:
            notifier.notify_if_needed(
                {"discount_type": "免单"},
            )

        mocked_at_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
