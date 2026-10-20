"""Allocating order lines to warehouses.

Lines are allocated one at a time, in the order ``orders.allocation_order``
gives them, against the stock left by the lines before them:

- a regular line takes what it can from each of its warehouses in turn
  (``routing.sources_for``), so it may ship from several, and what is left
  is backordered;
- a line of a ship-complete order (B2B pallets) ships from a single
  warehouse that can fill it entirely, or is backordered;
- a kit ships from a single warehouse that has every component for the
  whole quantity, or is backordered.
"""

import logging
from collections import Counter

from . import catalog, ledger, policy, routing
from .models import Allocation, Pick

log = logging.getLogger(__name__)

NO_SOURCE = "no warehouse stocks it"
NO_STOCK = "not enough stock"
PARTIAL = "partly in stock"


def _allocation(line, picks, backordered, reason=""):
    return Allocation(
        order_id=line.order_id,
        line_no=line.line_no,
        sku=line.sku,
        channel=line.channel,
        service=line.service,
        ordered=line.qty,
        picks=tuple(picks),
        backordered=backordered,
        reason=reason,
    )


def allocate_split(line, sources):
    need = line.qty
    picks = []
    for warehouse in sources:
        take = min(need, policy.allocatable(line.sku, warehouse, line.channel))
        if take:
            ledger.reserve(line.sku, warehouse, take)
            picks.append(Pick(warehouse, line.sku, take))
            need -= take
        if need == 0:
            break
    reason = "" if need == 0 else (PARTIAL if picks else NO_STOCK)
    return _allocation(line, picks, need, reason)


def allocate_complete(line, sources):
    for warehouse in sources:
        if policy.allocatable(line.sku, warehouse, line.channel) >= line.qty:
            ledger.reserve(line.sku, warehouse, line.qty)
            return _allocation(line, [Pick(warehouse, line.sku, line.qty)], 0)
    return _allocation(line, [], line.qty, NO_STOCK)


def allocate_kit(line, sources):
    parts = [(component, units * line.qty) for component, units in catalog.components(line.sku)]
    for warehouse in sources:
        if all(policy.allocatable(c, warehouse, line.channel) >= qty for c, qty in parts):
            picks = []
            for component, qty in parts:
                ledger.reserve(component, warehouse, qty)
                picks.append(Pick(warehouse, component, qty))
            return _allocation(line, picks, 0)
    return _allocation(line, [], line.qty, NO_STOCK)


def allocate_line(line):
    sources = routing.sources_for(line)
    if not sources:
        return _allocation(line, [], line.qty, NO_SOURCE)
    if catalog.is_kit(line.sku):
        return allocate_kit(line, sources)
    if line.ship_complete:
        return allocate_complete(line, sources)
    return allocate_split(line, sources)


def allocate_all(lines):
    allocations = []
    outcome = Counter()
    for line in lines:
        allocation = allocate_line(line)
        allocations.append(allocation)
        if allocation.backordered == 0:
            outcome["allocated"] += 1
        elif allocation.picks:
            outcome["partly allocated"] += 1
        else:
            outcome["backordered"] += 1
    log.info(
        "allocated %d lines: %d in full, %d in part, %d backordered",
        len(allocations),
        outcome["allocated"],
        outcome["partly allocated"],
        outcome["backordered"],
    )
    return allocations
