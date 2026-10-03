"""Money in minor units.

The processor sends amounts as decimal strings in the currency's major unit
("12.50"). The ledger keeps integer minor units throughout and only formats
them for the reports.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

EXPONENTS = {
    "EUR": 2, "USD": 2, "GBP": 2, "CHF": 2, "PLN": 2, "CZK": 2, "SEK": 2,
    "DKK": 2, "NOK": 2, "HUF": 2, "JPY": 0, "TRY": 2,
}


class MoneyError(ValueError):
    pass


def exponent(currency):
    try:
        return EXPONENTS[currency]
    except KeyError:
        raise MoneyError(f"unknown currency {currency!r}") from None


def to_minor(value, currency):
    """Parse a decimal string (or an int of minor units) into minor units."""
    if isinstance(value, int):
        return value
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation:
        raise MoneyError(f"bad amount {value!r}") from None
    scaled = amount.scaleb(exponent(currency))
    if scaled != scaled.to_integral_value():
        raise MoneyError(f"{value!r} has more decimals than {currency} allows")
    return int(scaled)


def basis_points(amount, bp):
    """``amount`` × bp / 10,000, rounded half up to the minor unit."""
    if not bp or not amount:
        return 0
    return int((Decimal(amount) * bp / Decimal(10000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def fmt(minor, currency="EUR"):
    exp = exponent(currency)
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    if exp == 0:
        return f"{sign}{minor:,}"
    major, cents = divmod(minor, 10 ** exp)
    return f"{sign}{major:,}.{cents:0{exp}d}"


def plain(minor, currency="EUR"):
    """Format for machine-readable files: no thousands separators."""
    return fmt(minor, currency).replace(",", "")
