import datetime as dt
import unittest
from unittest.mock import MagicMock, patch

from services.jubensha_booking.poster_scheduler import (
    BookingPosterScheduleError,
    next_booking_poster_run,
    start_booking_poster_scheduler,
)


class BookingPosterSchedulerTests(unittest.TestCase):
    def test_next_run_uses_later_time_today(self):
        now = dt.datetime(2026, 4, 23, 9, 30)

        result = next_booking_poster_run(now, ["10:01", "14:01", "20:01"])

        self.assertEqual(result, dt.datetime(2026, 4, 23, 10, 1))

    def test_next_run_rolls_to_tomorrow_after_last_time(self):
        now = dt.datetime(2026, 4, 23, 20, 2)

        result = next_booking_poster_run(now, ["10:01", "14:01", "20:01"])

        self.assertEqual(result, dt.datetime(2026, 4, 24, 10, 1))

    def test_next_run_rejects_invalid_time(self):
        with self.assertRaises(BookingPosterScheduleError):
            next_booking_poster_run(dt.datetime(2026, 4, 23, 9, 30), ["25:01"])

    def test_scheduler_sends_when_wait_finishes(self):
        wx = MagicMock()
        stop_event = _FakeStopEvent([False, True])
        now = dt.datetime(2026, 4, 23, 10, 1)

        with patch(
            "services.jubensha_booking.poster_scheduler.send_booking_poster_to_chat"
        ) as mocked_send:
            scheduler = start_booking_poster_scheduler(
                wx=wx,
                who="境由心造",
                schedule_times=["10:01"],
                stop_event=stop_event,
                clock=lambda: now,
                daemon=False,
                logger=lambda _: None,
            )
            scheduler.thread.join(timeout=2)

        mocked_send.assert_called_once_with(who="境由心造", wx=wx, exact=False)


class _FakeStopEvent:
    def __init__(self, wait_results):
        self._wait_results = list(wait_results)

    def wait(self, _timeout):
        return self._wait_results.pop(0)

    def is_set(self):
        return False

    def set(self):
        return None


if __name__ == "__main__":
    unittest.main()
