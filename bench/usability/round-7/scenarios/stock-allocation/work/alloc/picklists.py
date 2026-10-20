"""Pick lists for the warehouses' WMS.

One CSV per warehouse, dropped into the WMS inbox. Rows are grouped into
waves (express orders first, then ``wave_size`` orders per wave) and
sorted by bin within a wave, which is the order pickers walk the aisles.
"""

import csv
import logging
from pathlib import Path

from .models import EXPRESS, PickRow
from . import ledger

log = logging.getLogger(__name__)

FIELDS = ["wave", "order_id", "line_no", "sku", "bin", "qty"]


def assign_waves(allocations, warehouse, wave_size):
    """``{order_id: wave name}`` for the orders with picks in ``warehouse``."""
    express, standard = [], []
    seen = set()
    for allocation in allocations:
        if allocation.order_id in seen:
            continue
        if any(pick.warehouse == warehouse for pick in allocation.picks):
            seen.add(allocation.order_id)
            (express if allocation.service == EXPRESS else standard).append(allocation.order_id)
    waves = {}
    for prefix, orders in (("X", express), ("S", standard)):
        for index, order_id in enumerate(orders):
            waves[order_id] = f"{warehouse}-{prefix}{index // wave_size + 1:03d}"
    return waves


def pick_rows(allocations, warehouse, wave_size):
    waves = assign_waves(allocations, warehouse, wave_size)
    merged = {}
    for allocation in allocations:
        for pick in allocation.picks:
            if pick.warehouse != warehouse:
                continue
            key = (waves[allocation.order_id], allocation.order_id, allocation.line_no, pick.sku)
            merged[key] = merged.get(key, 0) + pick.qty
    rows = [
        PickRow(wave, order_id, line_no, sku, ledger.bin_of(sku, warehouse), qty)
        for (wave, order_id, line_no, sku), qty in merged.items()
        if qty > 0
    ]
    rows.sort(key=lambda row: (row.wave, row.bin, row.order_id, row.line_no))
    return rows


def write_pick_lists(out_dir, day, warehouses, allocations, wave_size):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for warehouse in warehouses:
        rows = pick_rows(allocations, warehouse, wave_size)
        path = out_dir / f"pick-{warehouse}-{day}.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            for row in rows:
                writer.writerow(row)
        written.append(path)
    log.info("wrote %d pick lists to %s", len(written), out_dir)
    return written
