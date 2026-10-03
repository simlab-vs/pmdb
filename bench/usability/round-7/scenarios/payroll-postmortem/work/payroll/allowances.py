"""Tax-free allowances.

Meal allowance: a fixed amount per weekday (Monday to Friday) on which the
person is employed and not absent.  Public holidays count as working days
for the allowance (the canteen subsidy contract says so).
"""

from .periods import is_weekday


def allowance_days(days, absent):
    return [day for day in days if is_weekday(day) and day not in absent]


def meal_allowance(days, absent, per_day):
    return len(allowance_days(days, absent)) * per_day
