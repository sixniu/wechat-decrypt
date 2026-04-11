import unittest
from unittest.mock import MagicMock, patch

from services.jubensha_booking.mysql_client import JubenshaMySQLClient
from services.jubensha_booking.service import JubenshaBookingService


class JubenshaBookingServiceTests(unittest.TestCase):
    def test_service_only_handles_text_messages_with_keywords(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = False
        service = JubenshaBookingService(mysql_client=mysql_client)

        service.handle_message(
            {
                "type": "文本",
                "content": "今天补贴局，7.23玩聚如故上车",
                "is_group": True,
                "sender": "顾飞雪",
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_called_once()

    def test_service_skips_non_group_messages(self):
        mysql_client = MagicMock()
        service = JubenshaBookingService(mysql_client=mysql_client)

        service.handle_message(
            {
                "type": "文本",
                "content": "今天补贴局，7.23玩聚如故上车",
                "is_group": False,
                "sender": "顾飞雪",
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_not_called()

    def test_service_skips_non_text_messages(self):
        mysql_client = MagicMock()
        service = JubenshaBookingService(mysql_client=mysql_client)

        service.handle_message(
            {
                "type": "图片",
                "content": "补贴",
                "is_group": True,
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_not_called()

    def test_service_uses_listener_sender_fields_for_booking_user(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = True
        service = JubenshaBookingService(mysql_client=mysql_client)

        result = {
            "data": [
                {
                    "user_name": "AI名字",
                    "user_id": "AI用户ID",
                    "booking_time": "2026-07-23 14:00",
                    "store_name": "玩聚",
                    "script_name": "如故",
                    "script_details": "原价上车",
                    "discount_type": "normal",
                    "wechat_no": "",
                }
            ]
        }

        with patch("services.jubensha_booking.service.extract_jubensha", return_value=result):
            service.handle_message(
                {
                    "type": "文本",
                    "content": "7.23玩聚如故=原价上车",
                    "is_group": True,
                    "sender": "顾飞雪",
                    "sender_id": "wxid_123",
                }
            )

        booking_item = mysql_client.upsert_booking.call_args.args[0]
        self.assertEqual(booking_item["user_name"], "顾飞雪")
        self.assertEqual(booking_item["user_id"], "wxid_123")
        self.assertEqual(booking_item["discount_type"], "正常")

    def test_service_prints_summary_when_minute_rolls(self):
        mysql_client = MagicMock()
        service = JubenshaBookingService(mysql_client=mysql_client)
        service._stats_bucket_minute = 100
        service._stats["matched"] = 2
        service._stats["ai_failed"] = 1

        with patch("services.jubensha_booking.service.time.time", return_value=61 * 101):
            with patch("builtins.print") as mocked_print:
                service._record_stat("skip_non_group")

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("[服务][剧本杀][分钟汇总]", printed)
        self.assertIn("命中处理=2", printed)
        self.assertIn("AI失败=1", printed)
        self.assertIn("跳过非群聊=0", printed)


class JubenshaMySQLClientTests(unittest.TestCase):
    def test_build_unique_numbers(self):
        self.assertEqual(
            len(JubenshaMySQLClient.build_raw_unique_no("wxid_123", "hello")),
            32,
        )
        self.assertEqual(
            len(
                JubenshaMySQLClient.build_booking_unique_no(
                    "2026-07-23 14:00",
                    "玩聚",
                    "如故",
                    "wxid_123",
                )
            ),
            32,
        )

    def test_insert_booking_uses_is_api_zero(self):
        executed = []

        class FakeCursor:
            def execute(self, sql, params=None):
                executed.append((sql, params))
                if "SELECT id FROM" in sql:
                    return None

            def fetchone(self):
                return None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeConnection:
            def cursor(self):
                return FakeCursor()

            def close(self):
                return None

        client = JubenshaMySQLClient(
            {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "pwd",
                "database": "demo",
                "charset": "utf8mb4",
            },
            raw_table="jubensha_all_content",
            booking_table="jubensha_booking",
        )

        with patch.object(client, "_connect", return_value=FakeConnection()):
            client.upsert_booking(
                {
                    "user_name": "顾飞雪",
                    "user_id": "wxid_123",
                    "booking_time": "2026-07-23 14:00",
                    "store_name": "玩聚",
                    "script_name": "如故",
                    "script_details": "原价上车",
                    "discount_type": "正常",
                    "wechat_no": "",
                }
            )

        insert_sql = executed[1][0]
        self.assertIn("0, %s", insert_sql)


if __name__ == "__main__":
    unittest.main()
