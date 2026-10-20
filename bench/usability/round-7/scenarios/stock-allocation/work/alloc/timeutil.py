"""Timestamps in the OMS export and the reports."""

from datetime import date, datetime, timezone


def parse_ts(text):
    """Parse an ISO 8601 timestamp; naive timestamps are UTC."""
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_day(text):
    return date.fromisoformat(text)


def utc_now():
    return datetime.now(timezone.utc)


def minutes_of(clock):
    """Minutes since midnight of an "HH:MM" string."""
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)
