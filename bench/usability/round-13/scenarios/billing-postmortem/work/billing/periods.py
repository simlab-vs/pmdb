"""Billing periods (calendar months) and day arithmetic."""

import calendar
from datetime import date, timedelta
from typing import NamedTuple


class Period(NamedTuple):
    """A billing month.

    ``start`` is the first day of the month and ``end`` the first day of the
    next month, both as ISO dates.  Readings taken on either day belong to the
    period: the closing read of one month is the opening read of the next.
    """

    label: str
    start: str
    end: str
    days: int


def parse_period(text):
    """Parse ``YYYY-MM`` into a :class:`Period`."""
    try:
        year, month = (int(part) for part in text.split("-"))
        first = date(year, month, 1)
    except ValueError as exc:
        raise ValueError(f"invalid billing period {text!r}, expected YYYY-MM") from exc
    days = calendar.monthrange(year, month)[1]
    following = first + timedelta(days=days)
    return Period(f"{year:04d}-{month:02d}", first.isoformat(), following.isoformat(), days)


def in_window(period, timestamp):
    """Whether a reading taken at ``timestamp`` (ISO) belongs to ``period``."""
    day = timestamp[:10]
    return period.start <= day <= period.end


def overlap_days(period, since="", until=""):
    """Days of ``period`` within ``[since, until)``; empty bounds are open."""
    first = max(period.start, since) if since else period.start
    last = min(period.end, until) if until else period.end
    if last <= first:
        return 0
    return (date.fromisoformat(last) - date.fromisoformat(first)).days


def fraction_of_period(period, days):
    """The share of the month covered by ``days``."""
    return days / period.days
