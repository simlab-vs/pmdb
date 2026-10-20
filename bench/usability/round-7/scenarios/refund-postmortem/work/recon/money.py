"""Money helpers: minor units, parsing and formatting."""

from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

MINOR_DIGITS = {
    "JPY": 0,
    "KRW": 0,
    "HUF": 2,
    "BHD": 3,
    "KWD": 3,
}
DEFAULT_MINOR_DIGITS = 2


class MoneyError(ValueError):
    pass


def minor_digits(currency):
    """Number of decimal digits of the minor unit of ``currency``."""
    return MINOR_DIGITS.get(currency.upper(), DEFAULT_MINOR_DIGITS)


def to_minor(value, currency):
    """Convert a decimal amount (string or Decimal) to integer minor units.

    Integers are taken to be minor units already.
    """
    if isinstance(value, bool):
        raise MoneyError(f"not an amount: {value!r}")
    if isinstance(value, int):
        return value
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise MoneyError(f"not an amount: {value!r}") from exc
    scaled = amount.scaleb(minor_digits(currency))
    if scaled != scaled.to_integral_value():
        raise MoneyError(f"too many decimals for {currency}: {value!r}")
    return int(scaled)


def from_minor(minor, currency):
    """Decimal value of ``minor`` units of ``currency``."""
    return Decimal(minor).scaleb(-minor_digits(currency))


def round_minor(value):
    """Round a Decimal number of minor units to an integer, half to even."""
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def fmt(minor, currency="EUR"):
    """Format minor units with a thousands separator, e.g. ``-1,234.50``."""
    value = from_minor(minor, currency)
    digits = minor_digits(currency)
    return f"{value:,.{digits}f}"
