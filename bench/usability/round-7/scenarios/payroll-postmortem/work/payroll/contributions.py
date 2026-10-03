"""Social security contributions.

Pension and unemployment insurance are levied on pay up to the pension
ceiling, health and care insurance up to the health ceiling.  Ceilings are
monthly; for a part month they are prorated by the days of employment
("SV-Tage", 30 for a full month).  Allowances are contribution-free.
"""

from .models import Contributions
from .money import percent_of

FULL_MONTH_DAYS = 30


def prorated_ceiling(ceiling, insured_days, month_length):
    if insured_days >= month_length:
        return ceiling
    return ceiling * min(insured_days, FULL_MONTH_DAYS) // FULL_MONTH_DAYS


def contributions(subject_pay, insured_days, month_length, rules):
    pension_base = min(subject_pay, prorated_ceiling(rules.pension_ceiling, insured_days, month_length))
    health_base = min(subject_pay, prorated_ceiling(rules.health_ceiling, insured_days, month_length))
    rates = rules.rates
    employee = (
        percent_of(pension_base, rates["pension_employee"])
        + percent_of(pension_base, rates["unemployment_employee"])
        + percent_of(health_base, rates["health_employee"])
        + percent_of(health_base, rates["care_employee"])
    )
    employer = (
        percent_of(pension_base, rates["pension_employer"])
        + percent_of(pension_base, rates["unemployment_employer"])
        + percent_of(health_base, rates["health_employer"])
        + percent_of(health_base, rates["care_employer"])
    )
    return Contributions(employee, employer, pension_base, health_base)
