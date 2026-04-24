"""剧本杀预约海报定时发送。"""

from __future__ import annotations

import datetime as dt
import random
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from .poster_sender import send_booking_poster_to_chats


class BookingPosterScheduleError(RuntimeError):
    """预约海报定时任务配置错误。"""


class StopEvent(Protocol):
    def wait(self, timeout: float) -> bool: ...

    def is_set(self) -> bool: ...

    def set(self) -> None: ...


@dataclass(frozen=True)
class BookingPosterScheduler:
    thread: threading.Thread
    stop_event: StopEvent

    def stop(self) -> None:
        self.stop_event.set()


def start_booking_poster_scheduler(
    *,
    wx,
    who_list: list[str] | tuple[str, ...],
    schedule_times: Iterable[str],
    exact: bool = False,
    stop_event: StopEvent | None = None,
    clock: Callable[[], dt.datetime] | None = None,
    random_delay_seconds: Callable[[], int] | None = None,
    logger: Callable[[str], None] = print,
    daemon: bool = True,
) -> BookingPosterScheduler:
    """启动后台线程，按指定时间每天发送预约海报到多个群聊。

    参数:
    - wx: 已初始化的 WeChat 实例。
    - who_list: 需要发送的目标群聊名称列表。
    - schedule_times: 每天发送时间列表，格式为 HH:MM。
    - exact: 搜索群聊时是否精确匹配。
    - stop_event: 外部可传入的停止事件，便于测试或手动停止。
    - clock: 当前时间函数，默认使用系统时间。
    - random_delay_seconds: 随机延后秒数函数，默认每次发送前随机 1-180 秒。
    - logger: 日志输出函数。
    - daemon: 是否以守护线程方式运行。
    """
    if wx is None:
        raise BookingPosterScheduleError("wx 必须传入已初始化的 WeChat 实例")

    times = tuple(schedule_times)
    _parse_schedule_times(times)
    targets = _normalize_who_list(who_list)
    event = stop_event or threading.Event()
    now = clock or dt.datetime.now
    delay_seconds = random_delay_seconds or (lambda: random.randint(1, 180))

    def _run() -> None:
        while not event.is_set():
            run_at = next_booking_poster_run_with_random_delay(
                now(),
                times,
                random_delay_seconds=delay_seconds,
            )
            wait_seconds = max(0.0, (run_at - now()).total_seconds())
            logger(
                "[services][jubensha][poster] 下次发送时间: "
                f"{run_at.strftime('%Y-%m-%d %H:%M:%S')}，目标群: {targets}"
            )
            if event.wait(wait_seconds):
                break
            try:
                # 到点后请求一次海报，再复用同一张图片依次发给所有目标群聊。
                send_booking_poster_to_chats(who_list=targets, wx=wx, exact=exact)
                logger(f"[services][jubensha][poster] 海报已发送到: {targets}")
            except Exception as exc:  # noqa: BLE001
                logger(f"[services][jubensha][poster] 海报发送失败: {exc}")

    thread = threading.Thread(
        target=_run,
        name="jubensha-booking-poster",
        daemon=daemon,
    )
    thread.start()
    return BookingPosterScheduler(thread=thread, stop_event=event)


def next_booking_poster_run(
    now: dt.datetime,
    schedule_times: Iterable[str],
) -> dt.datetime:
    """计算从 now 开始的下一次发送时间。"""
    parsed_times = _parse_schedule_times(schedule_times)
    today = now.date()

    for item in parsed_times:
        candidate = dt.datetime.combine(today, item)
        if candidate >= now:
            return candidate

    return dt.datetime.combine(today + dt.timedelta(days=1), parsed_times[0])


def next_booking_poster_run_with_random_delay(
    now: dt.datetime,
    schedule_times: Iterable[str],
    *,
    random_delay_seconds: Callable[[], int] | None = None,
) -> dt.datetime:
    """计算下一次带随机延后的海报发送时间。

    参数:
    - now: 当前时间，用于判断下一个基础发送时刻。
    - schedule_times: 每天基础发送时间列表，格式为 HH:MM。
    - random_delay_seconds: 可选的随机延后秒数函数；不传时每次调用随机返回 1-180 秒。

    返回值:
    - 返回基础发送时间加随机延后后的 datetime。

    失败行为:
    - schedule_times 为空或格式非法时，会抛出 BookingPosterScheduleError。
    """
    delay_seconds = random_delay_seconds or (lambda: random.randint(1, 180))
    base_run_at = next_booking_poster_run(now, schedule_times)
    return base_run_at + dt.timedelta(seconds=delay_seconds())


def _parse_schedule_times(schedule_times: Iterable[str]) -> tuple[dt.time, ...]:
    """把 HH:MM 字符串列表解析并排序为 time 元组。"""
    parsed: list[dt.time] = []
    for raw in schedule_times:
        try:
            hour_text, minute_text = str(raw).split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
            parsed.append(dt.time(hour=hour, minute=minute))
        except (TypeError, ValueError) as exc:
            raise BookingPosterScheduleError(f"无效发送时间: {raw}") from exc

    if not parsed:
        raise BookingPosterScheduleError("发送时间不能为空")

    return tuple(sorted(parsed))


def _normalize_who_list(who_list: list[str] | tuple[str, ...]) -> list[str]:
    """规范化目标群聊列表，去掉空值并保持原有顺序。"""
    targets = [str(item).strip() for item in who_list if str(item).strip()]
    if not targets:
        raise BookingPosterScheduleError("发送目标 who_list 不能为空")
    return targets
