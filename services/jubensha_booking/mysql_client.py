"""剧本杀服务的 MySQL 访问层。"""

from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any


class JubenshaMySQLClient:
    """封装原始消息去重和业务入库。"""

    def __init__(
        self,
        mysql_config: dict[str, Any],
        *,
        raw_table: str,
        booking_table: str,
    ) -> None:
        self._mysql_config = {
            "host": mysql_config["host"],
            "port": int(mysql_config.get("port", 3306)),
            "user": mysql_config["user"],
            "password": mysql_config["password"],
            "database": mysql_config["database"],
            "charset": mysql_config.get("charset", "utf8mb4"),
            "autocommit": True,
        }
        self._raw_table = raw_table
        self._booking_table = booking_table

    def _connect(self):
        try:
            import pymysql
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("未安装 PyMySQL，请先执行 `pip install PyMySQL`。") from exc

        return pymysql.connect(**self._mysql_config)

    @staticmethod
    def build_raw_unique_no(sender_wx_id: str, content: str) -> str:
        return hashlib.md5(f"{sender_wx_id}{content}".encode("utf-8")).hexdigest()

    @staticmethod
    def build_booking_unique_no(
        booking_time: str,
        store_name: str,
        script_name: str,
        user_id: str,
    ) -> str:
        raw = f"{booking_time}_{store_name}_{script_name}_{user_id}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def reserve_raw_message(
        self,
        *,
        sender_name: str,
        sender_wx_id: str,
        content: str,
    ) -> bool:
        """写入原始消息；已存在则返回 False。"""
        unique_no = self.build_raw_unique_no(sender_wx_id, content)
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT id FROM `{self._raw_table}` WHERE unique_no=%s LIMIT 1",
                    (unique_no,),
                )
                if cursor.fetchone():
                    return False

                cursor.execute(
                    f"""
                    INSERT INTO `{self._raw_table}` (
                        unique_no, sender_name, sender_wx_id, content
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (unique_no, sender_name, sender_wx_id, content),
                )
                return True
        finally:
            conn.close()

    def upsert_booking(self, item: dict[str, Any]) -> dict[str, Any]:
        """按业务唯一键插入或更新拼本记录。

        参数:
        - item: 已标准化的拼本业务数据，包含用户、时间、门店、剧本和优惠类型等字段。

        返回值:
        - 返回包含 unique_no、created、updated 的字典；created=True 表示本次新增。

        失败行为:
        - 数据库连接或 SQL 执行失败时抛出底层异常，由上层服务记录错误。
        """
        unique_no = self.build_booking_unique_no(
            item["booking_time"],
            item["store_name"],
            item["script_name"],
            item["user_id"],
        )
        expire_time = self._build_expire_time(item["booking_time"])
        now = self._current_timestamp()
        booking_type = str(item.get("booking_type") or "group").strip() or "group"

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id FROM `{self._booking_table}`
                    WHERE unique_no=%s AND deleted_at IS NULL
                    LIMIT 1
                    """,
                    (unique_no,),
                )
                row = cursor.fetchone()
                params = (
                    unique_no,
                    item["user_name"],
                    item["user_id"],
                    item["booking_time"],
                    item["store_name"],
                    item["script_name"],
                    item["script_details"],
                    item["discount_type"],
                    expire_time,
                    now,
                    now,
                    item["wechat_no"],
                    booking_type,
                    0,
                )
                if row:
                    cursor.execute(
                        f"""
                        UPDATE `{self._booking_table}`
                        SET user_name=%s,
                            user_id=%s,
                            booking_time=%s,
                            store_name=%s,
                            script_name=%s,
                            script_details=%s,
                            discount_type=%s,
                            expire_time=%s,
                            wechat_no=%s,
                            booking_type=%s,
                            updated_at=%s
                        WHERE unique_no=%s
                        """,
                        (
                            item["user_name"],
                            item["user_id"],
                            item["booking_time"],
                            item["store_name"],
                            item["script_name"],
                            item["script_details"],
                            item["discount_type"],
                            expire_time,
                            item["wechat_no"],
                            booking_type,
                            now,
                            unique_no,
                        ),
                    )
                    return {
                        "unique_no": unique_no,
                        "created": False,
                        "updated": True,
                    }
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO `{self._booking_table}` (
                            unique_no, user_name, user_id, booking_time, store_name,
                            script_name, script_details, discount_type, expire_time,
                            created_at, updated_at, is_api, wechat_no, booking_type,
                            is_completed
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s)
                        """,
                        params,
                    )
                    return {
                        "unique_no": unique_no,
                        "created": True,
                        "updated": False,
                    }
        finally:
            conn.close()

    @staticmethod
    def _build_expire_time(_booking_time: str) -> str:
        # 过期时间按收集入库时间计算，不跟开本时间绑定。
        value = dt.datetime.now()
        return (value + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _current_timestamp() -> str:
        return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
