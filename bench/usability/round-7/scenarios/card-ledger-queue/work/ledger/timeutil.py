"""Timestamps.

The processor sends ISO-8601 timestamps in UTC (``2026-09-28T14:03:11Z``).
Queue attributes carry epoch milliseconds.
"""

from datetime import date, datetime, timedelta, timezone


def parse_ts(value):
    """Epoch seconds of an ISO-8601 timestamp or date (a date means its midnight UTC)."""
    text = value.strip()
    if len(text) == 10:
        day = date.fromisoformat(text)
        return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp())


def from_millis(value):
    return int(value) // 1000


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def business_window(business_date):
    """``[start, end)`` of a business date, in epoch seconds (UTC days)."""
    day = date.fromisoformat(business_date)
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return int(start.timestamp()), int((start + timedelta(days=1)).timestamp())
