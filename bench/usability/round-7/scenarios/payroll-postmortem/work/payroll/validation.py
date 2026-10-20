"""Plausibility checks on the HR export before anything is paid."""

import logging
import re

from .models import ABSENCE_KINDS, HOURLY, PAY_TYPES, SALARIED

log = logging.getLogger(__name__)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")


class ValidationError(ValueError):
    pass


def iban_ok(iban):
    if not _IBAN.match(iban):
        return False
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def validate_person(person, cost_centres):
    """Raise ValidationError if the person's master data can't be paid."""
    problems = []
    if person.tax_class not in range(1, 7):
        problems.append(f"tax class {person.tax_class}")
    if not iban_ok(person.iban):
        problems.append("invalid IBAN")
    if not person.assignments:
        problems.append("no assignment")
    for row in person.assignments:
        problems.extend(row_problems(row, cost_centres))
    for absence in person.absences:
        if absence.kind not in ABSENCE_KINDS:
            problems.append(f"absence kind {absence.kind!r}")
        if not (_ISO_DATE.match(absence.first) and _ISO_DATE.match(absence.last)) or absence.last < absence.first:
            problems.append(f"absence {absence.first}..{absence.last}")
    if problems:
        raise ValidationError(f"{person.id}: " + "; ".join(problems))


def row_problems(row, cost_centres):
    problems = []
    if row.pay_type not in PAY_TYPES:
        problems.append(f"{row.id}: pay type {row.pay_type!r}")
    if row.pay_type == SALARIED and row.monthly_salary <= 0:
        problems.append(f"{row.id}: salaried without monthly salary")
    if row.pay_type == HOURLY and row.hourly_rate <= 0:
        problems.append(f"{row.id}: hourly without rate")
    if not 0 < row.weekly_hours <= 48:
        problems.append(f"{row.id}: weekly hours {row.weekly_hours}")
    if row.cost_centre not in cost_centres:
        problems.append(f"{row.id}: unknown cost centre {row.cost_centre}")
    if not _ISO_DATE.match(row.valid_from):
        problems.append(f"{row.id}: valid_from {row.valid_from!r}")
    if row.valid_to is not None and (not _ISO_DATE.match(row.valid_to) or row.valid_to < row.valid_from):
        problems.append(f"{row.id}: valid_to {row.valid_to!r}")
    return problems
