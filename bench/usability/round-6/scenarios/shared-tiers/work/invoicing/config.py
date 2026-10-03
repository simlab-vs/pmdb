"""Run configuration: billing period, seller settings and tax rules."""

import calendar
import json
from datetime import date
from pathlib import Path
from typing import NamedTuple


class Period(NamedTuple):
    label: str
    start: str
    end: str
    days: int


class Settings(NamedTuple):
    seller_country: str
    base_currency: str
    invoice_prefix: str
    vat_rates: dict
    eu_countries: tuple
    minimum_invoice: float
    payment_terms_days: int


class ConfigError(ValueError):
    pass


def parse_period(label):
    """Parse a period label such as ``2026-09`` into its first and last day."""
    try:
        year, month = (int(part) for part in label.split("-"))
    except ValueError:
        raise ConfigError(f"invalid period {label!r}, expected YYYY-MM") from None
    if not 1 <= month <= 12:
        raise ConfigError(f"invalid month in period {label!r}")
    days = calendar.monthrange(year, month)[1]
    return Period(
        label=f"{year:04d}-{month:02d}",
        start=date(year, month, 1).isoformat(),
        end=date(year, month, days).isoformat(),
        days=days,
    )


def load_settings(path):
    """Read ``settings.json`` and check the fields the run depends on."""
    raw = json.loads(Path(path).read_text())
    missing = [key for key in ("seller_country", "base_currency", "vat_rates") if key not in raw]
    if missing:
        raise ConfigError(f"settings.json lacks {', '.join(missing)}")
    vat_rates = {country.upper(): float(rate) for country, rate in raw["vat_rates"].items()}
    if raw["seller_country"].upper() not in vat_rates:
        raise ConfigError("no VAT rate for the seller's own country")
    return Settings(
        seller_country=raw["seller_country"].upper(),
        base_currency=raw["base_currency"].upper(),
        invoice_prefix=raw.get("invoice_prefix", "INV"),
        vat_rates=vat_rates,
        eu_countries=tuple(sorted(c.upper() for c in raw.get("eu_countries", []))),
        minimum_invoice=float(raw.get("minimum_invoice", 0)),
        payment_terms_days=int(raw.get("payment_terms_days", 30)),
    )


def days_between(first, last):
    """Number of days from ``first`` to ``last``, both ISO dates, counting both ends."""
    return (date.fromisoformat(last) - date.fromisoformat(first)).days + 1
