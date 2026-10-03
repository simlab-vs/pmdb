"""Reading the OMS export of open order lines.

The OMS exports every order with lines still waiting for allocation, one
order per line of JSON::

    {"order_id": "W-1029384", "channel": "web", "service": "express",
     "country": "DE", "created_at": "2026-09-28T21:13:08Z",
     "ship_complete": false, "hold": false,
     "lines": [{"line_no": 1, "sku": "KT-1043", "qty": 2, "status": "open"}]}

Marketplace lines count listings, and a listing may be a multipack:
``pack_size`` units of the SKU per listing (``"qty": 2, "pack_size": 3`` is
six units). Orders on hold (payment or fraud review) and lines that are not
``open`` are left for the next run.
"""

import json
import logging
from collections import Counter

from . import catalog
from .models import OrderLine, CHANNELS, EXPRESS, STANDARD

log = logging.getLogger(__name__)


class OrderError(ValueError):
    pass


def read_orders(path):
    with open(path, encoding="utf-8") as handle:
        for number, text in enumerate(handle, 1):
            text = text.strip()
            if not text:
                continue
            try:
                yield json.loads(text)
            except json.JSONDecodeError as exc:
                raise OrderError(f"{path}:{number}: {exc}") from exc


def order_lines(orders, stats):
    """Yield the allocatable ``OrderLine``s of the exported orders."""
    seen = set()
    for order in orders:
        stats["orders"] += 1
        if order.get("hold"):
            stats["held orders"] += 1
            continue
        channel = order.get("channel")
        if channel not in CHANNELS:
            stats["unknown channel"] += 1
            continue
        service = order.get("service", STANDARD)
        if service not in (EXPRESS, STANDARD):
            service = STANDARD
        for line in order.get("lines", ()):
            key = (order["order_id"], line["line_no"])
            if key in seen:
                stats["duplicate lines"] += 1
                continue
            seen.add(key)
            if line.get("status", "open") != "open":
                stats["lines not open"] += 1
                continue
            if not catalog.known(line["sku"]):
                stats["unknown SKU"] += 1
                log.warning("order %s line %s: unknown SKU %s", key[0], key[1], line["sku"])
                continue
            qty = int(line["qty"]) * int(line.get("pack_size", 1))
            if qty <= 0:
                stats["non-positive quantity"] += 1
                continue
            stats["lines"] += 1
            yield OrderLine(
                order_id=order["order_id"],
                line_no=int(line["line_no"]),
                sku=line["sku"],
                qty=qty,
                channel=channel,
                service=service,
                country=order.get("country", "").upper(),
                created_at=order["created_at"],
                ship_complete=bool(order.get("ship_complete", False)),
            )


def allocation_order(lines, express_first=True):
    """Lines in the order they get stock: express first, then first come, first served."""

    def key(line):
        rank = 0 if (express_first and line.service == EXPRESS) else 1
        return (rank, line.created_at, line.order_id, line.line_no)

    return sorted(lines, key=key)


def load_lines(path, express_first=True):
    stats = Counter()
    lines = allocation_order(order_lines(read_orders(path), stats), express_first)
    log.info("read %d orders, %d open lines from %s", stats["orders"], stats["lines"], path)
    skipped = {k: v for k, v in stats.items() if k not in ("orders", "lines")}
    if skipped:
        log.info("left for the next run: %s", ", ".join(f"{v} {k}" for k, v in sorted(skipped.items())))
    by_channel = Counter(line.channel for line in lines)
    log.info("lines by channel: %s", ", ".join(f"{c} {by_channel[c]}" for c in CHANNELS))
    return lines
