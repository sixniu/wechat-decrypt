import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
