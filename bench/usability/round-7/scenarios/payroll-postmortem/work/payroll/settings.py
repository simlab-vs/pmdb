"""Payroll rules from ``config/payroll.toml``."""

import tomllib
from typing import NamedTuple

from .money import parse_amount


class Rules(NamedTuple):
    company: str
    debtor_iban: str
    report_dir: str
    bank_dir: str
    cost_centres: dict
    meal_per_day: int
    night_bp: int
    sunday_bp: int
    holiday_bp: int
    overtime_bp: int
    night_from: int
    night_to: int
    pension_ceiling: int
    health_ceiling: int
    rates: dict
    tax_allowance: dict
    tax_bands: tuple
    holidays: frozenset


def minutes_of(clock):
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def load_rules(path):
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    company = raw["company"]
    premiums = raw["premiums"]
    contributions = raw["contributions"]
    rates = {
        key: value
        for key, value in contributions.items()
        if key.endswith("_employee") or key.endswith("_employer")
    }
    return Rules(
        company=company["name"],
        debtor_iban=company["debtor_iban"],
        report_dir=company["report_dir"],
        bank_dir=company["bank_dir"],
        cost_centres=dict(raw["cost_centres"]),
        meal_per_day=parse_amount(raw["allowances"]["meal_per_day"]),
        night_bp=premiums["night"],
        sunday_bp=premiums["sunday"],
        holiday_bp=premiums["holiday"],
        overtime_bp=premiums["overtime"],
        night_from=minutes_of(premiums["night_from"]),
        night_to=minutes_of(premiums["night_to"]),
        pension_ceiling=parse_amount(contributions["pension_ceiling"]),
        health_ceiling=parse_amount(contributions["health_ceiling"]),
        rates=rates,
        tax_allowance={int(cls): parse_amount(v) for cls, v in raw["tax"]["allowance"].items()},
        tax_bands=tuple((parse_amount(width), bp) for width, bp in raw["tax"]["bands"]),
        holidays=frozenset(raw["holidays"]["dates"]),
    )
