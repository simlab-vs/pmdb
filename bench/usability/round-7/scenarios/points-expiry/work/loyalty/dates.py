"""Calendar arithmetic on ISO dates (``YYYY-MM-DD`` strings).

ISO dates compare and sort correctly as strings, so lots and ledger entries
keep them as text; these helpers convert only to do arithmetic. A run asks
about the same few hundred dates for tens of thousands of lots, so the
month arithmetic is cached.
"""

import calendar
from datetime import date, timedelta
from functools import lru_cache


def parse(day):
    return date.fromisoformat(day)


def fmt(value):
    return value.isoformat()


def month_key(day):
    """``2026-09-30`` -> ``2026-09``."""
    return day[:7]


@lru_cache(maxsize=4096)
def first_of_month(day):
    return day[:8] + "01"


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


@lru_cache(maxsize=4096)
def end_of_month(day):
    d = parse(day)
    return fmt(d.replace(day=days_in_month(d.year, d.month)))


@lru_cache(maxsize=4096)
def is_month_end(day):
    return day == end_of_month(day)


@lru_cache(maxsize=4096)
def add_months(day, months):
    """Shift a date by whole months, clamping the day to the target month's length."""
    d = parse(day)
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return fmt(date(year, month, min(d.day, days_in_month(year, month))))


def next_day(day):
    return fmt(parse(day) + timedelta(days=1))


def month_range(day):
    """First and last day of the month containing ``day``."""
    return first_of_month(day), end_of_month(day)


@lru_cache(maxsize=4096)
def next_month_end(day):
    return end_of_month(add_months(first_of_month(day), 1))


def months_between(earlier, later):
    a, b = parse(earlier), parse(later)
    return (b.year - a.year) * 12 + (b.month - a.month)
