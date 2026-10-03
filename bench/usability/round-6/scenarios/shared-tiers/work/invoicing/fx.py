"""Exchange rates for invoices issued in a currency other than the base currency."""

import json
from pathlib import Path

from .money import round_cents


class FxError(LookupError):
    pass


def load_rates(path, period, base_currency):
    """Return ``{currency: rate}`` for the period, the base currency mapping to 1."""
    raw = json.loads(Path(path).read_text())
    if raw.get("base") != base_currency:
        raise FxError(f"fx.json is based on {raw.get('base')}, expected {base_currency}")
    try:
        month = raw["periods"][period.label]
    except KeyError:
        raise FxError(f"no exchange rates for {period.label}") from None
    rates = {currency.upper(): float(rate) for currency, rate in month.items()}
    rates[base_currency] = 1.0
    return rates


def convert(amount, currency, rates):
    """Convert an amount in the base currency, rounded to cents."""
    try:
        rate = rates[currency]
    except KeyError:
        raise FxError(f"no exchange rate for {currency}") from None
    return round_cents(amount * rate)
