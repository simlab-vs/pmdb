"""Money amounts.

Amounts are integers in minor units (cents, rappen, pence).  Prices in the
data files are decimal strings such as ``"12.90"``.
"""

from decimal import Decimal, ROUND_HALF_UP

SYMBOLS = {"EUR": "€", "CHF": "CHF ", "GBP": "£"}


class MoneyError(ValueError):
    """A price in the data files can't be read."""


def parse_amount(text):
    """Return the amount ``text`` (e.g. ``"12.90"``) in minor units."""
    if isinstance(text, int):
        return text * 100
    try:
        value = Decimal(str(text).strip())
    except Exception as exc:
        raise MoneyError(f"not an amount: {text!r}") from exc
    if value != value.quantize(Decimal("0.01")):
        raise MoneyError(f"more than two decimals: {text!r}")
    if value < 0:
        raise MoneyError(f"negative amount: {text!r}")
    return int(value * 100)


def format_amount(cents):
    """Format ``cents`` as a decimal string with two decimals."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def display(cents, currency):
    """Format ``cents`` for people, with the currency's symbol."""
    return f"{SYMBOLS.get(currency, currency + ' ')}{format_amount(cents)}"


def percent_of(cents, percent):
    """Return ``percent`` % of ``cents``, rounded half up to a whole cent."""
    exact = Decimal(cents) * Decimal(str(percent)) / Decimal(100)
    return int(exact.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def apply_discount(cents, percent):
    """Return ``cents`` reduced by ``percent`` %."""
    return cents - percent_of(cents, percent)
