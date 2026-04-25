"""微信自动化客户端封装。

这个文件负责封装 wxautox4 的常用发送能力，属于 services 通用服务层。
业务模块只需要调用这里的函数，不直接依赖 `wx.SendFiles`、`wx.SendMsg`
等底层方法，方便后续统一补充发送文本、艾特全体、发送语音等能力。
"""

from __future__ import annotations

from typing import Any


class WechatClientError(RuntimeError):
    """微信自动化调用失败。

    这个异常由微信发送封装函数抛出，通常由业务服务捕获并转换成自己的业务异常，
    用于隐藏 wxautox4 的具体异常类型，同时保留中文错误说明。
    """


def send_file(
    *,
    wx: Any | None,
    filepath: str | list[str],
    who: str | None = None,
    exact: bool = False,
) -> Any:
    """发送本地文件到微信聊天对象。

    参数:
    - wx: 已初始化的 WeChat 实例，由启动入口创建后传入。
    - filepath: 要发送文件的绝对路径，或多个绝对路径组成的列表。
    - who: 目标群聊或联系人名称；不传时发送给当前聊天对象。
    - exact: 搜索 who 好友或群聊时是否精确匹配。

    返回值:
    - 返回 wxautox4 的 `WxResponse` 调用结果，调用方可据此判断是否成功。

    失败行为:
    - wx 未传入、文件路径为空或 wxautox4 调用失败时抛出 WechatClientError。
    """
    _require_wx(wx)
    if _is_empty_filepath(filepath):
        raise WechatClientError("发送文件路径 filepath 不能为空")

    try:
        # 这里会触发真实微信文件发送，调用方必须确保 who 和 filepath 已确认无误。
        return wx.SendFiles(filepath=filepath, who=who, exact=exact)
    except Exception as exc:  # noqa: BLE001
        raise WechatClientError(f"发送微信文件失败: {exc}") from exc


def send_text(
    *,
    wx: Any | None,
    msg: str,
    who: str | None = None,
    clear: bool = True,
    at: str | list[str] | None = None,
    exact: bool = False,
) -> Any:
    """发送文本消息到微信聊天对象。

    参数:
    - wx: 已初始化的 WeChat 实例，由启动入口创建后传入。
    - msg: 要发送的文本消息内容。
    - who: 目标群聊或联系人名称；不传时发送给当前聊天对象。
    - clear: 发送后是否清空输入框。
    - at: 需要艾特的对象名称，支持单个名称或名称列表；不传则不艾特任何人。
    - exact: 搜索 who 好友或群聊时是否精确匹配。

    返回值:
    - 返回 wxautox4 的 `WxResponse` 调用结果，调用方可据此判断是否成功。

    失败行为:
    - wx 未传入、消息为空或 wxautox4 调用失败时抛出 WechatClientError。
    """
    _require_wx(wx)
    if not str(msg or "").strip():
        raise WechatClientError("消息内容 msg 不能为空")

    try:
        # 这里会触发真实微信文本发送，at 参数由 wxautox4 负责解析为艾特对象。
        return wx.SendMsg(msg=msg, who=who, clear=clear, at=at, exact=exact)
    except Exception as exc:  # noqa: BLE001
        raise WechatClientError(f"发送微信文本消息失败: {exc}") from exc


def at_all(
    *,
    wx: Any | None,
    msg: str,
    who: str | None = None,
    exact: bool = False,
) -> Any:
    """向微信群发送艾特全体消息。

    参数:
    - wx: 已初始化的 WeChat 实例，由启动入口创建后传入。
    - msg: 要发送的通知消息内容。
    - who: 目标群聊名称；不传时发送给当前聊天对象。
    - exact: 搜索 who 群聊时是否精确匹配。

    返回值:
    - 返回 wxautox4 的 `WxResponse` 调用结果，调用方可据此判断是否成功。

    失败行为:
    - wx 未传入、消息为空或 wxautox4 调用失败时抛出 WechatClientError。
    """
    _require_wx(wx)
    if not str(msg or "").strip():
        raise WechatClientError("艾特全体消息内容 msg 不能为空")

    try:
        # 这里会触发微信群 @所有人，调用前应确认目标群聊和消息内容。
        return wx.AtAll(msg, who, exact=exact)
    except Exception as exc:  # noqa: BLE001
        raise WechatClientError(f"发送微信艾特全体消息失败: {exc}") from exc


def _require_wx(wx: Any | None) -> None:
    """校验微信客户端实例。

    参数:
    - wx: 调用方传入的 WeChat 实例。

    返回值:
    - 无返回值；校验失败时抛出 WechatClientError。
    """
    if wx is None:
        raise WechatClientError("wx 必须传入已初始化的 WeChat 实例")


def _is_empty_filepath(filepath: str | list[str]) -> bool:
    """判断发送文件路径是否为空。

    参数:
    - filepath: 单个文件路径或多个文件路径列表。

    返回值:
    - 路径为空或列表中没有有效路径时返回 True，否则返回 False。
    """
    if isinstance(filepath, list):
        return not any(str(item or "").strip() for item in filepath)
    return not str(filepath or "").strip()
