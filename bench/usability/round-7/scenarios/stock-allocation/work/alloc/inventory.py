"""Client of the inventory service.

The service reports, per warehouse and SKU, the units on hand, the units
already reserved for orders in picking, the safety stock planned for the
SKU in that warehouse, the pick bin and the location status. It is read
once at the start of the run (``GET /levels?warehouse=..&page=..``).

For offline runs and tests the same records can be read from a dump file
(``inventory-cli dump --all > levels.json``), passed as ``--levels-file``:

    {"generated_at": "...", "levels": [{"sku": "KT-1043", "warehouse": "LEJ",
      "on_hand": 14, "reserved": 3, "safety_stock": 4, "bin": "B-12-03",
      "status": "active"}, ...]}
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

from .models import Level

log = logging.getLogger(__name__)

# Locations in these states can't be picked from; their stock counts as zero.
UNAVAILABLE_STATUSES = frozenset({"counting", "blocked", "quarantine"})


class InventoryError(RuntimeError):
    pass


def to_level(record):
    status = record.get("status", "active")
    on_hand = int(record.get("on_hand", 0))
    reserved = int(record.get("reserved", 0))
    available = max(0, on_hand - reserved)
    if status in UNAVAILABLE_STATUSES:
        available = 0
    return Level(
        sku=record["sku"],
        warehouse=record["warehouse"],
        on_hand=on_hand,
        reserved=reserved,
        available=available,
        safety_stock=max(0, int(record.get("safety_stock", 0))),
        bin=record.get("bin", ""),
        status=status,
    )


def _get_json(url, timeout, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts:
                raise InventoryError(f"GET {url}: {exc}") from exc
            log.warning("GET %s failed (%s), retrying", url, exc)
            time.sleep(2 * attempt)


def fetch_records(base_url, warehouses, timeout, page_size):
    """Yield the level records of the given warehouses from the service."""
    for warehouse in warehouses:
        page = 1
        while True:
            query = urllib.parse.urlencode({"warehouse": warehouse, "page": page, "page_size": page_size})
            body = _get_json(f"{base_url.rstrip('/')}/levels?{query}", timeout)
            yield from body.get("levels", ())
            if not body.get("next_page"):
                break
            page = body["next_page"]


def read_dump(path):
    with open(path, encoding="utf-8") as handle:
        body = json.load(handle)
    log.info("levels dump %s generated at %s", path, body.get("generated_at", "?"))
    return body.get("levels", [])


def load_levels(settings, levels_file=None, skus=None):
    """Return ``{(sku, warehouse): Level}`` for the configured warehouses."""
    warehouses = list(settings.warehouses)
    if levels_file:
        records = read_dump(levels_file)
        source = levels_file
    else:
        records = fetch_records(
            settings.inventory_url, warehouses, settings.inventory_timeout, settings.inventory_page_size
        )
        source = settings.inventory_url
    wanted = set(skus) if skus is not None else None
    levels = {}
    statuses = Counter()
    for record in records:
        if record.get("warehouse") not in settings.warehouses:
            continue
        if wanted is not None and record.get("sku") not in wanted:
            continue
        level = to_level(record)
        key = (level.sku, level.warehouse)
        if key in levels:
            raise InventoryError(f"two levels for {key}")
        levels[key] = level
        statuses[level.status] += 1
    log.info(
        "inventory: %d SKU locations from %s (%s)",
        len(levels),
        source,
        ", ".join(f"{n} {s}" for s, n in sorted(statuses.items())),
    )
    for code in warehouses:
        units = sum(l.available for l in levels.values() if l.warehouse == code)
        log.info("inventory: %s %d units available", code, units)
    return levels
