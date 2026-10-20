"""Records passed between the payroll stages.

Dates are ISO strings (``"2026-09-14"``) and amounts are integer cents
throughout; ``periods`` converts where calendar arithmetic is needed.
"""

from typing import NamedTuple, Optional

SALARIED = "salaried"
HOURLY = "hourly"
PAY_TYPES = (SALARIED, HOURLY)

UNPAID = "unpaid"
SICK = "sick"
VACATION = "vacation"
ABSENCE_KINDS = (UNPAID, SICK, VACATION)


class Assignment(NamedTuple):
    """One HR assignment row: the contract terms in force between two dates."""

    id: str
    person: str
    valid_from: str
    valid_to: Optional[str]
    pay_type: str
    monthly_salary: int
    hourly_rate: int
    weekly_hours: float
    cost_centre: str


class Absence(NamedTuple):
    person: str
    kind: str
    first: str
    last: str


class Person(NamedTuple):
    id: str
    name: str
    birth_date: str
    tax_class: int
    iban: str
    assignments: tuple
    absences: tuple


class Shift(NamedTuple):
    """One timesheet entry. ``end`` before ``start`` means the shift ended the next day."""

    person: str
    date: str
    start: str
    end: str
    break_minutes: int


class Employment(NamedTuple):
    person: str
    start: str
    end: Optional[str]
    segments: tuple


class Period(NamedTuple):
    month: str
    first: str
    last: str
    length: int


class HourlyPay(NamedTuple):
    pay: int
    premiums: int
    worked_minutes: int
    night_minutes: int
    sunday_minutes: int
    overtime_minutes: int
    paid_absence_days: int


class Contributions(NamedTuple):
    employee: int
    employer: int
    pension_base: int
    health_base: int


class Payslip(NamedTuple):
    person: str
    cost_centre: str
    pay_type: str
    days: int
    base_salary: int
    hourly_pay: int
    premiums: int
    allowances: int
    employee_contributions: int
    employer_contributions: int
    tax: int
    net: int

    @property
    def gross(self):
        return self.base_salary + self.hourly_pay + self.premiums + self.allowances
