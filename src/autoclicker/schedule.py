"""When a run starts and stops: right away, at a time of day, or after a countdown.

Pure Python (no Qt) so it's easy to test. Times are naive local datetimes; `.timestamp()` turns them
into wall-clock seconds, which keep counting while the computer sleeps (unlike time.monotonic on
some systems), so a run whose stop time passed during sleep ends as soon as the computer wakes up.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .i18n import tr

START_MODES = ("now", "at", "in")       # right away / at a time of day / after a countdown
STOP_MODES = ("none", "at", "after")    # no time limit / at a time of day / after running for


def next_clock(after: datetime, hour: int, minute: int, second: int = 0) -> datetime:
    """The first moment strictly after `after` when the clock shows hour:minute:second.
    19:30 asked at 18:00 -> today 19:30; asked at 20:00 -> tomorrow 19:30."""
    t = after.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if t <= after:
        t += timedelta(days=1)
    return t


def plan(now: datetime, start_mode: str, start_at: tuple[int, int], start_in: int,
         stop_mode: str, stop_at: tuple[int, int], stop_after: int) -> tuple[datetime, datetime | None]:
    """Returns (start, stop). stop is None when the run has no time limit.

    start_at / stop_at are (hour, minute); start_in / stop_after are seconds.
    The stop time counts from the start: "start at 19:30, stop at 01:00" stops the next night at
    01:00, and "stop after 01:30:00" means 1 h 30 of clicking, not counting the wait before it.
    """
    if start_mode == "at":
        start = next_clock(now, *start_at)
    elif start_mode == "in":
        start = now + timedelta(seconds=max(0, start_in))
    else:
        start = now
    if stop_mode == "at":
        stop = next_clock(start, *stop_at)
    elif stop_mode == "after":
        stop = start + timedelta(seconds=max(1, stop_after))
    else:
        stop = None
    return start, stop


def fmt_when(t: datetime, now: datetime) -> str:
    """'19:30', '19:30 tomorrow' or '19:30 Mon 30 Nov'; seconds only when they aren't :00."""
    clock = t.strftime("%H:%M:%S" if t.second else "%H:%M")
    days = (t.date() - now.date()).days
    if days == 0:
        return clock
    if days == 1:
        return tr("when_tomorrow", t=clock)
    return tr("when_date", t=clock, date=f"{t:%a %d %b}")
