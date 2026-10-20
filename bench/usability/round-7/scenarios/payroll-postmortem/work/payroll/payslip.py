"""One payslip per person employed in the period."""

import logging
from collections import Counter

from .absences import absence_days, paid_absence_days, unpaid_days
from .allowances import meal_allowance
from .contributions import contributions
from .employment import EmploymentError, employed_days, employment_for, segment_at
from .hourly import hourly_pay
from .models import Payslip
from .salaried import base_salary
from .tax import wage_tax
from .validation import ValidationError, validate_person

log = logging.getLogger(__name__)

STATS = Counter()


def pay_person(person, shifts, period, rules):
    """The person's Payslip for ``period``, or None if not employed in it."""
    employment = employment_for(person.id, person.assignments)
    days = employed_days(employment, period)
    if not days:
        return None
    absent = absence_days(person.absences, days)
    unpaid = unpaid_days(absent)
    base = base_salary(employment, days, unpaid, period.length)
    hourly = hourly_pay(employment, days, shifts, paid_absence_days(absent), rules)
    allowances = meal_allowance(days, absent, rules.meal_per_day)
    subject = base + hourly.pay + hourly.premiums
    contrib = contributions(subject, len(days), period.length, rules)
    tax = wage_tax(subject - contrib.employee, person.tax_class, rules)
    current = segment_at(employment.segments, days[-1])
    STATS["unpaid leave days"] += len(unpaid)
    STATS["worked minutes"] += hourly.worked_minutes
    STATS["night minutes"] += hourly.night_minutes
    STATS["overtime minutes"] += hourly.overtime_minutes
    STATS["paid absence days"] += hourly.paid_absence_days
    if len(days) < period.length:
        STATS["part-month"] += 1
    return Payslip(
        person=person.id,
        cost_centre=current.cost_centre,
        pay_type=current.pay_type,
        days=len(days),
        base_salary=base,
        hourly_pay=hourly.pay,
        premiums=hourly.premiums,
        allowances=allowances,
        employee_contributions=contrib.employee,
        employer_contributions=contrib.employer,
        tax=tax,
        net=subject + allowances - contrib.employee - tax,
    )


def compute_payslips(persons, shifts_by_person, period, rules):
    """Yield (person, payslip) for everyone employed in the period.

    Persons whose master data fails validation are reported and left out,
    so that one bad record doesn't hold up everyone's pay.
    """
    for person in persons:
        try:
            validate_person(person, rules.cost_centres)
            payslip = pay_person(person, shifts_by_person.get(person.id, ()), period, rules)
        except (ValidationError, EmploymentError) as exc:
            STATS["rejected"] += 1
            log.warning("not paid: %s", exc)
            continue
        if payslip is None:
            STATS["not employed"] += 1
            continue
        yield person, payslip
