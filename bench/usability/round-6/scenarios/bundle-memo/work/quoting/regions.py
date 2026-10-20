"""Sales regions: currency, price list, VAT and shipping per country."""

import json
from typing import NamedTuple

from .money import parse_amount


class Region(NamedTuple):
    code: str
    currency: str
    price_list: str
    vat_percent: str
    shipping_fee: int
    free_shipping_from: int


class RegionError(LookupError):
    """A customer's region isn't configured."""


def load_regions(path):
    """Read ``regions.json`` and return a dict from country code to Region."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    regions = {}
    for code, entry in raw.items():
        regions[code] = Region(
            code=code,
            currency=entry["currency"],
            price_list=entry["price_list"],
            vat_percent=str(entry["vat"]),
            shipping_fee=parse_amount(entry["shipping"]["fee"]),
            free_shipping_from=parse_amount(entry["shipping"]["free_from"]),
        )
    return regions


def region_of(regions, code):
    """Return the Region of country ``code``."""
    try:
        return regions[code.upper()]
    except KeyError:
        raise RegionError(f"no sales region for country {code!r}") from None
