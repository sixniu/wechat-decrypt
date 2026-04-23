import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import json

import monitor_web_new


class MonitorContactAliasTests(unittest.TestCase):
    def test_load_contact_alias_reads_one_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "contact.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE contact (username TEXT, alias TEXT)")
            conn.execute(
                "INSERT INTO contact(username, alias) VALUES (?, ?)",
                ("wxid_s1rc1q8dj19h22", "sblyx0519"),
            )
            conn.execute(
                "INSERT INTO contact(username, alias) VALUES (?, ?)",
                ("wxid_other", "other_alias"),
            )
            conn.commit()
            conn.close()

            with patch.object(monitor_web_new, "CONTACT_CACHE", db_path):
                self.assertEqual(
                    monitor_web_new.load_contact_alias("wxid_s1rc1q8dj19h22"),
                    "sblyx0519",
                )
                self.assertEqual(monitor_web_new.load_contact_alias("missing"), "")

    def test_session_monitor_caches_alias_after_single_lookup(self):
        monitor = monitor_web_new.SessionMonitor(
            enc_key=b"",
            session_db="session.db",
            contact_names={},
            contact_aliases={},
        )

        with patch.object(
            monitor_web_new,
            "load_contact_alias",
            return_value="sblyx0519",
        ) as mocked:
            self.assertEqual(
                monitor._resolve_contact_alias("wxid_s1rc1q8dj19h22"),
                "sblyx0519",
            )
            self.assertEqual(
                monitor._resolve_contact_alias("wxid_s1rc1q8dj19h22"),
                "sblyx0519",
            )

        mocked.assert_called_once_with("wxid_s1rc1q8dj19h22", None)


class MonitorBookingPosterSchedulerTests(unittest.TestCase):
    def test_start_booking_poster_scheduler_uses_enabled_config(self):
        wx = MagicMock()
        cfg = {
            "services": {
                "jubensha_booking": {
                    "poster_sender": {
                        "enabled": True,
                        "target_chat": "境由心造",
                        "exact": False,
                        "times": ["10:01", "14:01", "20:01"],
                    }
                }
            }
        }

        with patch.object(monitor_web_new, "load_service_config", return_value=cfg):
            with patch.object(
                monitor_web_new,
                "start_booking_poster_scheduler",
            ) as mocked_start:
                monitor_web_new.start_booking_poster_scheduler_if_enabled(wx)

        mocked_start.assert_called_once_with(
            wx=wx,
            who="境由心造",
            schedule_times=["10:01", "14:01", "20:01"],
            exact=False,
        )

    def test_reload_runtime_service_config_restarts_services_and_poster_scheduler(self):
        wx = MagicMock()
        cfg = {
            "services": {
                "jubensha_booking": {
                    "poster_sender": {
                        "enabled": True,
                        "target_chat": "新群",
                        "exact": True,
                        "times": ["11:01"],
                    }
                }
            }
        }
        old_scheduler = MagicMock()

        with patch.object(monitor_web_new, "BOOKING_POSTER_SCHEDULER", old_scheduler):
            with patch.object(
                monitor_web_new,
                "load_service_config_strict",
                return_value=cfg,
            ):
                with patch.object(monitor_web_new, "shutdown_service_manager") as mocked_shutdown:
                    with patch.object(
                        monitor_web_new,
                        "start_booking_poster_scheduler",
                    ) as mocked_start:
                        result = monitor_web_new.reload_runtime_service_config(wx)

        self.assertTrue(result)
        mocked_shutdown.assert_called_once_with(wait=False)
        old_scheduler.stop.assert_called_once_with()
        mocked_start.assert_called_once_with(
            wx=wx,
            who="新群",
            schedule_times=["11:01"],
            exact=True,
        )

    def test_reload_runtime_service_config_keeps_current_state_on_bad_json(self):
        wx = MagicMock()
        old_scheduler = MagicMock()

        with patch.object(monitor_web_new, "BOOKING_POSTER_SCHEDULER", old_scheduler):
            with patch.object(
                monitor_web_new,
                "load_service_config_strict",
                side_effect=json.JSONDecodeError("bad", "{", 0),
            ):
                with patch.object(monitor_web_new, "shutdown_service_manager") as mocked_shutdown:
                    result = monitor_web_new.reload_runtime_service_config(wx)

        self.assertFalse(result)
        mocked_shutdown.assert_not_called()
        old_scheduler.stop.assert_not_called()

    def test_runtime_config_reloader_reloads_when_config_mtime_changes(self):
        wx = MagicMock()
        stop_event = _FakeStopEvent([False, True])

        with patch.object(
            monitor_web_new,
            "_get_config_mtime",
            side_effect=[1.0, 2.0],
        ):
            with patch.object(
                monitor_web_new,
                "reload_runtime_service_config",
                return_value=True,
            ) as mocked_reload:
                reloader = monitor_web_new.start_runtime_config_reloader(
                    wx,
                    interval_seconds=0,
                    stop_event=stop_event,
                    daemon=False,
                )
                reloader.thread.join(timeout=2)

        mocked_reload.assert_called_once_with(wx)


class _FakeStopEvent:
    def __init__(self, wait_results):
        self._wait_results = list(wait_results)

    def wait(self, _timeout):
        return self._wait_results.pop(0)

    def set(self):
        return None


if __name__ == "__main__":
    unittest.main()
