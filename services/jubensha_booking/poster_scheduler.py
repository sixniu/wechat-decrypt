"""剧本杀预约海报定时发送。"""

from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from .poster_sender import send_booking_poster_to_chat


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
    who: str,
    schedule_times: Iterable[str],
    exact: bool = False,
    stop_event: StopEvent | None = None,
    clock: Callable[[], dt.datetime] | None = None,
    logger: Callable[[str], None] = print,
    daemon: bool = True,
) -> BookingPosterScheduler:
    """启动后台线程，按指定时间每天发送预约海报。"""
    if wx is None:
        raise BookingPosterScheduleError("wx 必须传入已初始化的 WeChat 实例")

    times = tuple(schedule_times)
    _parse_schedule_times(times)
    event = stop_event or threading.Event()
    now = clock or dt.datetime.now

    def _run() -> None:
        while not event.is_set():
            run_at = next_booking_poster_run(now(), times)
            wait_seconds = max(0.0, (run_at - now()).total_seconds())
            logger(
                "[services][jubensha][poster] 下次发送时间: "
                f"{run_at.strftime('%Y-%m-%d %H:%M:%S')}，目标群: {who}"
            )
            if event.wait(wait_seconds):
                break
            try:
                send_booking_poster_to_chat(who=who, wx=wx, exact=exact)
                logger(f"[services][jubensha][poster] 海报已发送到: {who}")
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


def _parse_schedule_times(schedule_times: Iterable[str]) -> tuple[dt.time, ...]:
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
