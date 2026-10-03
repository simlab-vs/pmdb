"""Amounts are carried as floats and rounded to cents only on invoice lines."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def round_cents(amount):
    """Round half up to two decimals, as the accounting system does."""
    return float(Decimal(repr(amount)).quantize(CENT, rounding=ROUND_HALF_UP))


def format_amount(amount, currency):
    """Format an amount for invoice texts, e.g. ``1,234.50 EUR``."""
    return f"{amount:,.2f} {currency}"


def format_rate(rate):
    """Format a unit price without trailing zeros, e.g. ``0.00045``."""
    text = f"{rate:.6f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def sum_amounts(amounts):
    """Sum rounded amounts and round the result again to absorb float noise."""
    return round_cents(sum(amounts))


def percent_of(amount, fraction):
    """``fraction`` of ``amount``, rounded to cents."""
    return round_cents(amount * fraction)
