"""Absences (unpaid leave, sickness, vacation) within the pay period."""

from .models import SICK, UNPAID, VACATION
from .periods import date_range

# When two absences cover the same day, the one that costs the employee
# least wins: a sick day during unpaid leave is paid as sick.
PRECEDENCE = {SICK: 0, VACATION: 1, UNPAID: 2}


def absence_days(absences, days):
    """Map each of ``days`` covered by an absence to the absence kind."""
    wanted = set(days)
    covered = {}
    for absence in absences:
        if absence.last < days[0] or absence.first > days[-1]:
            continue
        for day in date_range(max(absence.first, days[0]), min(absence.last, days[-1])):
            if day not in wanted:
                continue
            kind = covered.get(day)
            if kind is None or PRECEDENCE[absence.kind] < PRECEDENCE[kind]:
                covered[day] = absence.kind
    return covered


def unpaid_days(covered):
    return {day for day, kind in covered.items() if kind == UNPAID}


def paid_absence_days(covered):
    """Days of sickness or vacation, paid to hourly staff at their contract hours."""
    return sorted(day for day, kind in covered.items() if kind in (SICK, VACATION))
