"""Reading the HR system's monthly payroll export.

The HR system exports one JSON document per pay period::

    {
      "exported_at": "2026-09-30T18:00:02Z",
      "period": "2026-09",
      "persons": [
        {
          "id": "P10417",
          "name": "…", "birth_date": "1988-02-11", "tax_class": 1,
          "iban": "DE…",
          "assignments": [
            {"id": "A20811", "valid_from": "2024-03-01", "valid_to": null,
             "pay_type": "salaried", "monthly_salary": "4310.00",
             "weekly_hours": 40, "cost_centre": "CC-210"},
            …
          ],
          "absences": [{"kind": "unpaid", "from": "2026-09-07", "to": "2026-09-09"}, …]
        },
        …
      ],
      "timesheets": [
        {"person": "P10522", "date": "2026-09-01", "start": "22:00", "end": "06:15", "break": 30},
        …
      ]
    }

``pay_type`` is ``salaried`` (``monthly_salary``) or ``hourly``
(``hourly_rate``); amounts are decimal strings in EUR.  ``valid_to`` and an
absence's ``to`` are inclusive; ``valid_to`` is null while a row is open.
Persons who left before the period may still be listed.  Timesheets are
the approved entries of the period for hourly staff.
"""

import json
import logging
from collections import defaultdict

from .models import Absence, Assignment, Person, Shift
from .money import parse_amount

log = logging.getLogger(__name__)


class ExportError(ValueError):
    pass


def read_export(path):
    """Return (persons, shifts by person id) from the export at ``path``."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    try:
        persons = [person_from(item) for item in raw["persons"]]
        shifts = defaultdict(list)
        for item in raw.get("timesheets", []):
            shift = shift_from(item)
            shifts[shift.person].append(shift)
    except (KeyError, TypeError) as exc:
        raise ExportError(f"{path}: malformed export ({exc!r})") from exc
    rows = sum(len(person.assignments) for person in persons)
    log.info(
        "read %d persons, %d assignment rows, %d absences and %d timesheet entries from %s (exported %s)",
        len(persons),
        rows,
        sum(len(person.absences) for person in persons),
        sum(len(entries) for entries in shifts.values()),
        path,
        raw.get("exported_at", "?"),
    )
    return persons, dict(shifts), raw.get("period")


def person_from(item):
    return Person(
        id=item["id"],
        name=item.get("name", ""),
        birth_date=item["birth_date"],
        tax_class=int(item["tax_class"]),
        iban=item["iban"].replace(" ", ""),
        assignments=tuple(assignment_from(item["id"], row) for row in item["assignments"]),
        absences=tuple(absence_from(item["id"], row) for row in item.get("absences", [])),
    )


def assignment_from(person_id, row):
    return Assignment(
        id=row["id"],
        person=person_id,
        valid_from=row["valid_from"],
        valid_to=row.get("valid_to"),
        pay_type=row["pay_type"],
        monthly_salary=parse_amount(row.get("monthly_salary", "0")),
        hourly_rate=parse_amount(row.get("hourly_rate", "0")),
        weekly_hours=float(row["weekly_hours"]),
        cost_centre=row["cost_centre"],
    )


def absence_from(person_id, row):
    return Absence(person_id, row["kind"], row["from"], row["to"])


def shift_from(item):
    return Shift(item["person"], item["date"], item["start"], item["end"], int(item.get("break", 0)))
