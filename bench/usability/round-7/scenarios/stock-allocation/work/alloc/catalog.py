"""Product master data: SKU attributes and kit compositions.

``catalog/skus.csv`` has one row per sellable SKU with its handling
attributes; ``catalog/kits.csv`` lists the components of kit SKUs (bundles
assembled from stocked components at picking time).
"""

import csv
import logging
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class Sku(NamedTuple):
    sku: str
    name: str
    hazmat: bool
    bulky: bool
    active: bool


_skus = {}
_kits = {}


def _flag(value):
    return value.strip().lower() in ("1", "y", "yes", "true")


def load_catalog(directory):
    directory = Path(directory)
    _skus.clear()
    _kits.clear()
    with open(directory / "skus.csv", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            _skus[row["sku"]] = Sku(
                sku=row["sku"],
                name=row["name"],
                hazmat=_flag(row["hazmat"]),
                bulky=_flag(row["bulky"]),
                active=_flag(row.get("active", "1")),
            )
    with open(directory / "kits.csv", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            _kits.setdefault(row["kit"], []).append((row["component"], int(row["qty"])))
    for kit, components in _kits.items():
        missing = [c for c, _ in components if c not in _skus]
        if missing:
            raise ValueError(f"kit {kit} has unknown components {missing}")
    log.info("catalog: %d SKUs, %d kits", len(_skus), len(_kits))
    return len(_skus), len(_kits)


def known(sku):
    return sku in _skus


def attributes(sku):
    return _skus[sku]


def is_kit(sku):
    return sku in _kits


def components(sku):
    """``[(component, units per kit)]`` of a kit SKU."""
    return list(_kits[sku])


def stocked_skus():
    """SKUs whose stock levels the run needs: everything but the kits themselves."""
    return sorted(s for s in _skus if s not in _kits)
