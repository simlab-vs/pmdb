"""Employment periods from HR assignment rows."""

from bisect import bisect_right

from .models import Employment
from .periods import period_days


class EmploymentError(ValueError):
    pass


def employment_for(person_id, rows):
    """Build a person's Employment from their assignment rows.

    HR keeps one assignment row per contract state: a change of pay, hours
    or cost centre closes the current row and opens the next one, so a
    person's rows follow each other without overlapping.  The employment
    runs from the first row's start to the last row's end (``None`` while
    the last row is open), and ``segments`` are the rows in date order.
    """
    rows = sorted(rows, key=lambda row: row.valid_from)
    for previous, row in zip(rows, rows[1:]):
        if previous.valid_to is None or previous.valid_to >= row.valid_from:
            raise EmploymentError(f"{person_id}: assignments {previous.id} and {row.id} overlap")
    return Employment(person_id, rows[0].valid_from, rows[-1].valid_to, tuple(rows))


def employed_days(employment, period):
    """The period's days (ISO dates) on which the person is employed."""
    first = max(employment.start, period.first)
    last = period.last if employment.end is None else min(employment.end, period.last)
    return [day for day in period_days(period) if first <= day <= last]


def segment_at(segments, day):
    """The assignment row in force on ``day``; ``segments`` sorted by start."""
    starts = [segment.valid_from for segment in segments]
    index = bisect_right(starts, day) - 1
    if index < 0:
        raise EmploymentError(f"{segments[0].person}: no assignment on {day}")
    return segments[index]


def pay_type_on(employment, day):
    return segment_at(employment.segments, day).pay_type
