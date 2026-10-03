"""Products and price lists.

The catalog of a run is loaded once with :func:`load_catalog` and then
read through the functions of this module.
"""

import csv
import json
import os
from typing import NamedTuple

from .money import parse_amount

TIERS = ("retail", "member", "trade")

_products = {}
_price_lists = {}
_list_of_region = {}


class Product(NamedTuple):
    sku: str
    name: str
    category: str
    groups: tuple
    active: bool


class CatalogError(LookupError):
    """A product or a price is missing."""


def product(sku):
    """Return the Product ``sku``."""
    try:
        return _products[sku]
    except KeyError:
        raise CatalogError(f"unknown SKU {sku!r}") from None


def in_group(sku, group):
    """Whether ``sku`` belongs to the product group ``group``."""
    return group in product(sku).groups


def group_members(group):
    """The SKUs of the product group ``group``, sorted."""
    return sorted(sku for sku, p in _products.items() if group in p.groups)


def price_list_id(region_code):
    """The id of the price list used for customers in ``region_code``."""
    try:
        return _list_of_region[region_code]
    except KeyError:
        raise CatalogError(f"no price list for region {region_code!r}") from None


def unit_price(sku, ctx):
    """Return the price of one unit of ``sku`` for the context ``ctx``.

    A tier without its own price pays the retail price.
    """
    prices = _price_lists[price_list_id(ctx.region)]["prices"]
    try:
        entry = prices[sku]
    except KeyError:
        raise CatalogError(f"{sku} has no price for {ctx.region}") from None
    return entry.get(ctx.tier, entry["retail"])


def combo_price(offer_id, ctx):
    """Return the price of the combo ``offer_id`` for ``ctx``, or None."""
    return _price_lists[price_list_id(ctx.region)]["combos"].get(offer_id)


def price_list_count():
    return len(_price_lists)


def _read_products(path):
    products = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            groups = tuple(g for g in row["groups"].split(";") if g)
            products[row["sku"]] = Product(
                sku=row["sku"],
                name=row["name"],
                category=row["category"],
                groups=groups,
                active=row.get("active", "1") == "1",
            )
    return products


def _read_price_list(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    prices = {}
    for sku, entry in raw["prices"].items():
        if isinstance(entry, str):
            entry = {"retail": entry}
        unknown = set(entry) - set(TIERS)
        if unknown:
            raise CatalogError(f"{path}: unknown tiers {sorted(unknown)} for {sku}")
        prices[sku] = {tier: parse_amount(p) for tier, p in entry.items()}
    combos = {oid: parse_amount(p) for oid, p in raw.get("combos", {}).items()}
    return {"id": raw["id"], "currency": raw["currency"], "prices": prices, "combos": combos}


def load_catalog(directory, regions):
    """Load ``products.csv`` and the price lists in ``pricelists/``.

    ``regions`` maps country codes to their Region; every region's price
    list must exist and be in the region's currency.
    """
    products = _read_products(os.path.join(directory, "products.csv"))
    price_lists = {}
    list_dir = os.path.join(directory, "pricelists")
    for name in sorted(os.listdir(list_dir)):
        if name.endswith(".json"):
            pl = _read_price_list(os.path.join(list_dir, name))
            price_lists[pl["id"]] = pl
    for region in regions.values():
        pl = price_lists.get(region.price_list)
        if pl is None:
            raise CatalogError(f"region {region.code} uses missing price list {region.price_list}")
        if pl["currency"] != region.currency:
            raise CatalogError(
                f"region {region.code} is in {region.currency} but {pl['id']} is in {pl['currency']}"
            )
        missing = set(products) - set(pl["prices"])
        if missing:
            raise CatalogError(f"{pl['id']} has no price for {sorted(missing)[:5]}")
    _products.clear()
    _products.update(products)
    _price_lists.clear()
    _price_lists.update(price_lists)
    _list_of_region.clear()
    _list_of_region.update({code: r.price_list for code, r in regions.items()})
    return len(products)
