"""Pay periods (calendar months) and calendar helpers on ISO dates."""

import calendar
from datetime import date, timedelta

from .models import Period


class PeriodError(ValueError):
    pass


def parse_period(text):
    """``"2026-09"`` → Period(month, first day, last day, number of days)."""
    try:
        year, month = (int(part) for part in text.split("-"))
        length = calendar.monthrange(year, month)[1]
    except (ValueError, calendar.IllegalMonthError) as exc:
        raise PeriodError(f"not a period: {text!r}") from exc
    first = date(year, month, 1)
    return Period(f"{year:04d}-{month:02d}", first.isoformat(), date(year, month, length).isoformat(), length)


def period_days(period):
    first = date.fromisoformat(period.first)
    return [(first + timedelta(days=offset)).isoformat() for offset in range(period.length)]


def weekday(day):
    """0 = Monday … 6 = Sunday."""
    return date.fromisoformat(day).weekday()


def is_weekday(day):
    return weekday(day) < 5


def iso_week(day):
    year, week, _ = date.fromisoformat(day).isocalendar()
    return f"{year}-W{week:02d}"


def date_range(first, last):
    """ISO dates from ``first`` to ``last`` inclusive."""
    start, end = date.fromisoformat(first), date.fromisoformat(last)
    return [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]


def next_day(day):
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


def age_on(birth_date, day):
    born, on = date.fromisoformat(birth_date), date.fromisoformat(day)
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))
