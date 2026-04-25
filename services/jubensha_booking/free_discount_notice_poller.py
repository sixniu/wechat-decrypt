"""免单拼本通知任务轮询器。

这个文件属于 `jubensha_booking` 业务模块，负责让本地 wechat-decrypt
主动向服务器领取免单通知任务，并复用 `FreeDiscountNotifier` 完成微信
@所有人 发送。服务器只保存任务和状态，本文件不直接读写服务器数据库。
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .free_discount_notifier import FreeDiscountNotifier


class FreeDiscountNoticePollerError(RuntimeError):
    """免单通知轮询配置或接口调用错误。"""


class StopEvent(Protocol):
    """后台轮询线程使用的停止事件协议。"""

    def wait(self, timeout: float) -> bool: ...

    def is_set(self) -> bool: ...

    def set(self) -> None: ...


@dataclass(frozen=True)
class FreeDiscountNoticePollerRunner:
    """免单通知轮询后台任务句柄。

    该对象由 `start_free_discount_notice_poller` 返回，入口热加载配置时会调用
    `stop()` 停止旧线程，再按新配置启动新线程。
    """

    thread: threading.Thread
    stop_event: StopEvent

    def stop(self) -> None:
        """停止后台轮询线程。

        参数:
        - 无参数。

        返回值:
        - 无返回值；主要副作用是通知线程尽快退出循环。
        """
        self.stop_event.set()


class FreeDiscountNoticeHttpClient:
    """免单通知接口 HTTP 客户端。

    该类只负责和 script-kill-api 的内部接口通信，不包含微信发送逻辑。
    """

    def get_json(self, url: str, *, token: str, timeout: float) -> dict[str, Any]:
        """发送 GET 请求并解析 JSON 响应。

        参数:
        - url: 完整接口地址。
        - token: 内部接口 token，会放入 `X-Internal-Token` 请求头。
        - timeout: 请求超时时间，单位秒。

        返回值:
        - 返回接口 JSON 对象。

        失败行为:
        - 网络异常、JSON 非对象时抛出 `FreeDiscountNoticePollerError`。
        """
        return self._request_json("GET", url, None, token=token, timeout=timeout)

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        token: str,
        timeout: float,
    ) -> dict[str, Any]:
        """发送 POST JSON 请求并解析 JSON 响应。

        参数:
        - url: 完整接口地址。
        - payload: 需要提交的 JSON 对象。
        - token: 内部接口 token，会放入 `X-Internal-Token` 请求头。
        - timeout: 请求超时时间，单位秒。

        返回值:
        - 返回接口 JSON 对象。
        """
        return self._request_json("POST", url, payload, token=token, timeout=timeout)

    def _request_json(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        *,
        token: str,
        timeout: float,
    ) -> dict[str, Any]:
        """执行底层 HTTP 请求并解析 JSON。

        参数:
        - method: HTTP 方法，目前使用 GET 或 POST。
        - url: 完整接口地址。
        - payload: POST 请求体；GET 时传 None。
        - token: 内部接口 token。
        - timeout: 请求超时时间，单位秒。

        返回值:
        - 返回 JSON 字典。
        """
        body = None
        headers = {
            "Accept": "application/json",
            "X-Internal-Token": token,
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        try:
            request = Request(url, data=body, headers=headers, method=method)
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except URLError as exc:
            raise FreeDiscountNoticePollerError(f"免单通知接口请求失败: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FreeDiscountNoticePollerError("免单通知接口返回不是合法 JSON") from exc

        if not isinstance(data, dict):
            raise FreeDiscountNoticePollerError("免单通知接口返回必须是 JSON 对象")
        return data


class FreeDiscountNoticePoller:
    """免单通知任务轮询器。

    该类由启动入口按配置创建；它保存 API 地址、token、通知器和轮询参数。
    调用 `poll_once()` 会领取一批 pending 任务，逐条发送微信通知并回写状态。
    """

    def __init__(
        self,
        *,
        api_base_url: str,
        token: str,
        notifier: FreeDiscountNotifier,
        http_client: FreeDiscountNoticeHttpClient | Any | None = None,
        limit: int = 10,
        timeout: float = 10.0,
    ) -> None:
        """初始化免单通知轮询器。

        参数:
        - api_base_url: 服务器内部通知接口基础地址，例如 `https://域名/api/booking/free-notices`。
        - token: 内部接口 token。
        - notifier: 已注入微信客户端的免单通知器。
        - http_client: 可替换的 HTTP 客户端，测试中用于避免真实网络请求。
        - limit: 单次最多领取任务数。
        - timeout: 单次接口请求超时时间，单位秒。

        返回值:
        - 无返回值；保存轮询所需状态。
        """
        self._api_base_url = api_base_url.rstrip("/")
        self._token = token
        self._notifier = notifier
        self._http_client = http_client or FreeDiscountNoticeHttpClient()
        self._limit = min(50, max(1, int(limit)))
        self._timeout = float(timeout)

        if not self._api_base_url:
            raise FreeDiscountNoticePollerError("api_base_url 不能为空")
        if not self._token:
            raise FreeDiscountNoticePollerError("token 不能为空")

    def poll_once(self) -> None:
        """执行一次免单通知任务轮询。

        参数:
        - 无参数。

        返回值:
        - 无返回值；主要副作用是发送微信通知并向服务器回写 sent/failed 状态。
        """
        response = self._http_client.get_json(
            self._pending_url(),
            token=self._token,
            timeout=self._timeout,
        )
        if int(response.get("code", 0)) != 200:
            raise FreeDiscountNoticePollerError(
                str(response.get("msg") or "免单通知领取接口返回失败")
            )

        notices = response.get("data", {}).get("list", [])
        if not isinstance(notices, list):
            raise FreeDiscountNoticePollerError("免单通知领取接口 data.list 必须是数组")

        for notice in notices:
            if not isinstance(notice, dict):
                continue
            self._handle_notice(notice)

    def _handle_notice(self, notice: dict[str, Any]) -> None:
        """处理单条免单通知任务。

        参数:
        - notice: 服务器 pending 接口返回的单条任务数据。

        返回值:
        - 无返回值；发送成功会回写 sent，发送失败会回写 failed。
        """
        notice_id = int(notice.get("id") or 0)
        payload = notice.get("payload")
        if notice_id <= 0 or not isinstance(payload, dict):
            return

        try:
            # 这里会触发真实微信 @所有人，调用方已在启动前确保 target_chats 非空。
            self._notifier.notify_if_needed(payload)
            self._mark_sent(notice_id)
        except Exception as exc:  # noqa: BLE001
            self._mark_failed(notice_id, str(exc))

    def _pending_url(self) -> str:
        """拼接领取待发送任务的接口地址。

        参数:
        - 无参数。

        返回值:
        - 返回带 limit 参数的 pending 接口 URL。
        """
        return f"{self._api_base_url}/pending?{urlencode({'limit': self._limit})}"

    def _mark_sent(self, notice_id: int) -> None:
        """向服务器回写任务发送成功。

        参数:
        - notice_id: 通知任务主键。

        返回值:
        - 无返回值；接口失败时抛出轮询错误。
        """
        self._http_client.post_json(
            f"{self._api_base_url}/{notice_id}/sent",
            {},
            token=self._token,
            timeout=self._timeout,
        )

    def _mark_failed(self, notice_id: int, message: str) -> None:
        """向服务器回写任务发送失败。

        参数:
        - notice_id: 通知任务主键。
        - message: 失败原因摘要。

        返回值:
        - 无返回值；接口失败时由 HTTP 客户端抛出异常。
        """
        self._http_client.post_json(
            f"{self._api_base_url}/{notice_id}/failed",
            {"message": message[:1000]},
            token=self._token,
            timeout=self._timeout,
        )


def start_free_discount_notice_poller(
    *,
    poller: FreeDiscountNoticePoller,
    interval_seconds: float = 10.0,
    stop_event: StopEvent | None = None,
    logger: Callable[[str], None] = print,
    daemon: bool = True,
) -> FreeDiscountNoticePollerRunner:
    """启动免单通知后台轮询线程。

    参数:
    - poller: 已配置好的免单通知轮询器。
    - interval_seconds: 两次轮询之间的等待秒数。
    - stop_event: 可选停止事件，测试中可注入。
    - logger: 日志输出函数。
    - daemon: 是否以守护线程方式运行。

    返回值:
    - 返回后台线程句柄，调用 `stop()` 可停止后续轮询。
    """
    event = stop_event or threading.Event()
    interval = max(1.0, float(interval_seconds))

    def _run() -> None:
        while not event.is_set():
            try:
                # 每轮只请求一次 pending 接口，空列表时几乎不消耗流量。
                poller.poll_once()
            except Exception as exc:  # noqa: BLE001
                logger(f"[services][jubensha][free-poller] 轮询失败: {exc}")
            if event.wait(interval):
                break

    thread = threading.Thread(
        target=_run,
        name="jubensha-free-discount-poller",
        daemon=daemon,
    )
    thread.start()
    return FreeDiscountNoticePollerRunner(thread=thread, stop_event=event)
