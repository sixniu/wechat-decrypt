import datetime as dt
import time
import unittest
from unittest.mock import MagicMock, patch

from services.jubensha_booking.mysql_client import JubenshaMySQLClient
from services.jubensha_booking.service import JubenshaBookingService

REAL_DATETIME = dt.datetime
TEST_MONITORED_CHATROOM_IDS = ("18614995060@chatroom",)
TEST_TRIGGER_KEYWORDS = ("补贴", "上车")


def build_service(mysql_client, **kwargs):
    return JubenshaBookingService(
        mysql_client=mysql_client,
        monitored_chatroom_ids=kwargs.get(
            "monitored_chatroom_ids",
            TEST_MONITORED_CHATROOM_IDS,
        ),
        trigger_keywords=kwargs.get("trigger_keywords", TEST_TRIGGER_KEYWORDS),
        allowed_time_range=kwargs.get("allowed_time_range", ("09:30", "20:00")),
    )


class JubenshaBookingServiceTests(unittest.TestCase):
    def test_service_only_handles_text_messages_with_keywords(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = False
        service = build_service(mysql_client)

        service.handle_message(
            {
                "type": "文本",
                "content": "今天补贴局，7.23玩聚如故上车",
                "is_group": True,
                "chat_id": "18614995060@chatroom",
                "sender": "顾飞雪",
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_called_once()

    def test_service_skips_non_group_messages(self):
        mysql_client = MagicMock()
        service = build_service(mysql_client)

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
        service = build_service(mysql_client)

        service.handle_message(
            {
                "type": "图片",
                "content": "补贴",
                "is_group": True,
                "chat_id": "18614995060@chatroom",
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_not_called()

    def test_service_skips_unmonitored_group_messages(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = False
        service = build_service(mysql_client)

        with patch("builtins.print") as mocked_print:
            service.handle_message(
                {
                    "type": "文本",
                    "content": "今天补贴局，7.23玩聚如故上车",
                    "is_group": True,
                    "chat_id": "unmonitored@chatroom",
                    "sender": "顾飞雪",
                    "sender_id": "wxid_123",
                }
            )

        mysql_client.reserve_raw_message.assert_not_called()
        mocked_print.assert_not_called()

    def test_service_uses_configured_chatrooms_and_keywords(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = False
        service = build_service(
            mysql_client,
            monitored_chatroom_ids=("custom@chatroom",),
            trigger_keywords=("自定义关键词",),
        )

        service.handle_message(
            {
                "type": "文本",
                "content": "这里包含自定义关键词",
                "is_group": True,
                "chat_id": "custom@chatroom",
                "sender": "顾飞雪",
                "sender_id": "wxid_123",
            }
        )

        mysql_client.reserve_raw_message.assert_called_once()

    def test_service_skips_messages_outside_allowed_time_range(self):
        mysql_client = MagicMock()
        service = build_service(mysql_client, allowed_time_range=("09:30", "20:00"))

        with patch(
            "services.jubensha_booking.service.time.localtime",
            return_value=time.struct_time((2026, 4, 23, 21, 0, 0, 3, 113, -1)),
        ):
            service.handle_message(
                {
                    "type": "文本",
                    "content": "今天补贴局，7.23玩聚如故上车",
                    "is_group": True,
                    "chat_id": "18614995060@chatroom",
                    "sender": "顾飞雪",
                    "sender_id": "wxid_123",
                }
            )

        mysql_client.reserve_raw_message.assert_not_called()

    def test_service_uses_listener_sender_fields_for_booking_user(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = True
        service = build_service(mysql_client)

        result = {
            "data": [
                {
                    "booking_time": "2026-07-23 14:00",
                    "store_name": "玩聚",
                    "script_name": "如故",
                    "script_details": "原价上车",
                    "discount_type": "normal",
                }
            ]
        }

        with patch("services.jubensha_booking.service.extract_jubensha", return_value=result):
            service.handle_message(
                {
                    "type": "文本",
                    "content": "7.23玩聚如故=原价上车",
                    "is_group": True,
                    "chat_id": "18614995060@chatroom",
                    "sender": "顾飞雪",
                    "sender_id": "wxid_123",
                    "wechat_no": "sblyx0519",
                }
            )

        booking_item = mysql_client.upsert_booking.call_args.args[0]
        self.assertEqual(booking_item["user_name"], "顾飞雪")
        self.assertEqual(booking_item["user_id"], "wxid_123")
        self.assertEqual(booking_item["discount_type"], "正常")
        self.assertEqual(booking_item["wechat_no"], "sblyx0519")

    def test_service_ignores_ai_identity_fields(self):
        mysql_client = MagicMock()
        mysql_client.reserve_raw_message.return_value = True
        service = build_service(mysql_client)

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
                    "wechat_no": "ai-wechat",
                }
            ]
        }

        with patch("services.jubensha_booking.service.extract_jubensha", return_value=result):
            service.handle_message(
                {
                    "type": "文本",
                    "content": "7.23玩聚如故=原价上车",
                    "is_group": True,
                    "chat_id": "18614995060@chatroom",
                    "sender": "顾飞雪",
                    "sender_id": "wxid_123",
                }
            )

        booking_item = mysql_client.upsert_booking.call_args.args[0]
        self.assertEqual(booking_item["user_name"], "顾飞雪")
        self.assertEqual(booking_item["user_id"], "wxid_123")
        self.assertEqual(booking_item["wechat_no"], "")

    def test_service_prints_summary_when_minute_rolls(self):
        mysql_client = MagicMock()
        service = build_service(mysql_client)
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

    def test_expire_time_uses_current_time_plus_one_day(self):
        with patch("services.jubensha_booking.mysql_client.dt.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = REAL_DATETIME(2026, 4, 20, 10, 30, 0)
            mocked_datetime.strptime.side_effect = AssertionError(
                "expire_time should not be based on booking_time"
            )

            expire_time = JubenshaMySQLClient._build_expire_time("2026-12-31 20:00")

        self.assertEqual("2026-04-21 10:30:00", expire_time)

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

    def test_insert_booking_sets_laravel_timestamps_and_booking_defaults(self):
        executed = []

        class FakeCursor:
            def execute(self, sql, params=None):
                executed.append((sql, params))

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

        insert_sql, params = executed[1]
        self.assertIn("created_at", insert_sql)
        self.assertIn("updated_at", insert_sql)
        self.assertIn("booking_type", insert_sql)
        self.assertIn("is_completed", insert_sql)
        self.assertEqual("group", params[-2])
        self.assertEqual(0, params[-1])

    def test_update_booking_skips_soft_deleted_rows_and_touches_updated_at(self):
        executed = []

        class FakeCursor:
            def execute(self, sql, params=None):
                executed.append((sql, params))

            def fetchone(self):
                return (7,)

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

        select_sql = executed[0][0]
        update_sql = executed[1][0]
        self.assertIn("deleted_at IS NULL", select_sql)
        self.assertIn("updated_at=%s", update_sql)


if __name__ == "__main__":
    unittest.main()
