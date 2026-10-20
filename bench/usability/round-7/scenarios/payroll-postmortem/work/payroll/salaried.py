"""Base pay of salaried staff.

The monthly salary is paid pro rata by calendar days: each day of the
period on which the person is employed on a salaried row earns
1/(days in the month) of that row's monthly salary.  Days of unpaid leave
earn nothing; sickness and vacation are paid as usual.  A full month pays
exactly the monthly salary, whatever the month's length.
"""

from .employment import segment_at
from .models import SALARIED
from .money import round_half_up


def base_salary(employment, days, unpaid, month_length):
    """Prorated salary in cents for the employed ``days`` of the period."""
    earned = 0
    for day in days:
        if day in unpaid:
            continue
        segment = segment_at(employment.segments, day)
        if segment.pay_type != SALARIED:
            continue
        earned += segment.monthly_salary
    return round_half_up(earned, month_length)


def salaried_days(employment, days):
    return sum(1 for day in days if segment_at(employment.segments, day).pay_type == SALARIED)
