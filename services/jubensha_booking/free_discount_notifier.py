"""剧本杀免单通知器。

这个文件负责在剧本杀拼本业务数据新增后，针对 `discount_type=免单`
的记录向微信群发送 @所有人 通知。它属于 `jubensha_booking` 业务模块，
但实际微信发送动作委托给通用的 `services.wechat_client` 封装，避免业务
处理服务直接调用 wxautox4 方法。
"""

from __future__ import annotations

from typing import Any

from services.wechat_client import WechatClientError, at_all


class FreeDiscountNotifier:
    """免单拼本微信群通知器。

    这个类由服务注册表在启动 `JubenshaBookingService` 时创建并注入。
    它只保存微信客户端、目标群聊和匹配方式，不管理数据库状态；是否需要通知
    由调用方在业务数据成功新增后决定。未配置目标群聊时不会发送。
    """

    def __init__(
        self,
        *,
        wx: Any,
        target_chats: tuple[str, ...] = (),
        exact: bool = False,
    ) -> None:
        """初始化免单通知器。

        参数:
        - wx: 已初始化的 WeChat 实例，由监听入口创建后传入。
        - target_chats: 固定通知目标群聊；为空时不发送。
        - exact: 调用 wxautox4 搜索群聊时是否精确匹配。

        返回值:
        - 无返回值；保存后续发送通知所需的运行时状态。
        """
        self._wx = wx
        self._target_chats = target_chats
        self._exact = exact

    def notify_if_needed(
        self,
        booking_item: dict[str, Any],
    ) -> None:
        """在拼本记录为免单时发送 @所有人 通知。

        参数:
        - booking_item: 已成功新增入库的拼本业务数据。

        返回值:
        - 无返回值；满足条件时会向微信群发送 @所有人 通知。

        失败行为:
        - 微信发送失败时抛出 WechatClientError，由上层服务记录错误日志后继续处理。
        """
        if str(booking_item.get("discount_type") or "").strip() != "免单":
            return

        targets = self._resolve_targets()
        if not targets:
            return

        message = self._build_message(booking_item)
        for target in targets:
            # 这里会触发真实微信群 @所有人 通知，调用前已限定为新增免单记录。
            at_all(wx=self._wx, msg=message, who=target, exact=self._exact)

    def _resolve_targets(self) -> tuple[str, ...]:
        """解析本次通知要发送到哪些群聊。

        参数:
        - 无参数。

        返回值:
        - 返回固定配置的目标群聊；未配置时返回空元组。
        """
        return self._target_chats

    @staticmethod
    def _build_message(booking_item: dict[str, Any]) -> str:
        """构建免单通知文本。

        参数:
        - booking_item: 已成功新增入库的拼本业务数据。

        返回值:
        - 返回发送到微信群的通知文本。
        """
        booking_time = str(booking_item.get("booking_time") or "").strip() or "时间待确认"
        store_name = str(booking_item.get("store_name") or "").strip() or "门店待确认"
        script_name = str(booking_item.get("script_name") or "").strip() or "剧本待确认"
        script_details = str(booking_item.get("script_details") or "").strip()
        user_name = str(booking_item.get("user_name") or "").strip()

        lines = [
            "免单拼车提醒",
            f"时间：{booking_time}",
            f"门店：{store_name}",
            f"剧本：{script_name}",
        ]
        if script_details:
            lines.append(f"备注：{script_details}")
        if user_name:
            lines.append(f"发布人：{user_name}")
        return "\n".join(lines)
