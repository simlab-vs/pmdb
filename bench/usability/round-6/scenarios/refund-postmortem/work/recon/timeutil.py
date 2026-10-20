"""Time parsing and month windows. All timestamps are handled as UTC epochs."""

import calendar
from datetime import datetime, timezone


def parse_epoch(value):
    """Parse an epoch (int or digit string) or an ISO 8601 timestamp.

    Naive timestamps are taken to be UTC.
    """
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp())


def month_window(month):
    """Return ``(start, end)`` epochs of a ``YYYY-MM`` month, end exclusive."""
    year, mon = (int(part) for part in month.split("-"))
    start = calendar.timegm((year, mon, 1, 0, 0, 0))
    if mon == 12:
        year, mon = year + 1, 1
    else:
        mon += 1
    end = calendar.timegm((year, mon, 1, 0, 0, 0))
    return start, end


def day_of(ts):
    """The UTC calendar day of an epoch, as ``YYYY-MM-DD``."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
