"""Amounts in integer cents."""

import re

_AMOUNT = re.compile(r"^(-?)(\d+)(?:\.(\d{1,2}))?$")


class AmountError(ValueError):
    pass


def parse_amount(text):
    """Parse a decimal amount such as ``"4250.00"`` or ``"18.4"`` into cents."""
    if isinstance(text, int):
        return text * 100
    match = _AMOUNT.match(str(text).strip())
    if not match:
        raise AmountError(f"not an amount: {text!r}")
    sign, units, fraction = match.groups()
    cents = int(units) * 100 + int((fraction or "0").ljust(2, "0"))
    return -cents if sign else cents


def round_half_up(numerator, denominator):
    """``numerator / denominator`` rounded to the nearest integer, halves away from zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator < 0:
        return -round_half_up(-numerator, denominator)
    return (2 * numerator + denominator) // (2 * denominator)


def percent_of(amount, basis_points):
    """``amount`` × ``basis_points`` / 10,000, rounded half up (1 % = 100 basis points)."""
    return round_half_up(amount * basis_points, 10_000)


def fmt(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100:,}.{cents % 100:02d}"
