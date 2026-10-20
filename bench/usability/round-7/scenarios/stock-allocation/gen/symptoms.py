#!/usr/bin/env python3
"""What the warehouses saw: short picks and over-shipped lines of a run.

  symptoms.py PICK_DIR DAY LEVELS.json ORDERS.jsonl CATALOG_DIR

Short pick: a SKU location whose pick lists ask for more units than were
physically there to promise (on hand minus reserved, nothing in locations
under count or blocked). Over-shipped: an order line whose pick rows, over
all warehouses, add up to more units than were ordered.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

UNAVAILABLE = {"counting", "blocked", "quarantine"}


def main():
    pick_dir, day, levels_path, orders_path, catalog_dir = sys.argv[1:6]
    levels = json.load(open(levels_path))["levels"]
    physical = {}
    for r in levels:
        avail = max(0, r["on_hand"] - r["reserved"])
        if r["status"] in UNAVAILABLE:
            avail = 0
        physical[(r["sku"], r["warehouse"])] = avail
    kits = defaultdict(list)
    with open(Path(catalog_dir) / "kits.csv") as h:
        for row in csv.DictReader(h):
            kits[row["kit"]].append((row["component"], int(row["qty"])))
    ordered = {}
    channel = {}
    for text in open(orders_path):
        o = json.loads(text)
        for l in o["lines"]:
            l = dict(l, qty=l["qty"] * l.get("pack_size", 1))
            units = {c: q * l["qty"] for c, q in kits[l["sku"]]} if l["sku"] in kits else {l["sku"]: l["qty"]}
            ordered[(o["order_id"], int(l["line_no"]))] = units
            channel[o["order_id"]] = o["channel"]
    picked = Counter()
    shipped = defaultdict(Counter)
    shipped_by_wh = defaultdict(Counter)
    for path in sorted(Path(pick_dir).glob(f"pick-*-{day}.csv")):
        wh = path.name.split("-")[1]
        with open(path) as h:
            for row in csv.DictReader(h):
                q = int(row["qty"])
                picked[(row["sku"], wh)] += q
                key = (row["order_id"], int(row["line_no"]))
                shipped[key][row["sku"]] += q
                shipped_by_wh[key][wh] += q
    short = Counter()
    short_skus = defaultdict(set)
    for (sku, wh), q in picked.items():
        if q > physical.get((sku, wh), 0):
            short[wh] += q - physical.get((sku, wh), 0)
            short_skus[wh].add(sku)
    over_units = Counter()
    over_lines = Counter()
    over_orders = defaultdict(set)
    examples = []
    for key, units in shipped.items():
        extra = sum(max(0, q - ordered[key].get(sku, 0)) for sku, q in units.items())
        if extra:
            whs = shipped_by_wh[key]
            # attribute the extra units to the warehouse(s) that shipped the line last in its route
            for wh in whs:
                over_units[wh] += 0
            examples.append((key, dict(units), ordered[key], dict(whs), channel[key[0]]))
            over_lines[channel[key[0]]] += 1
            over_orders[channel[key[0]]].add(key[0])
            over_units["total"] += extra
    for wh in sorted(short):
        print(f"short {wh}: {short[wh]} units missing over {len(short_skus[wh])} SKUs")
    print(f"over-shipped: {over_units['total']} units on {sum(over_lines.values())} lines "
          f"of {sum(len(v) for v in over_orders.values())} orders by channel {dict(over_lines)}")
    per_wh = Counter()
    for key, units, want, whs, ch in examples:
        extra = sum(max(0, q - want.get(s, 0)) for s, q in units.items())
        # the extra units were packed where the line was topped up: the non-first warehouse
        per_wh[max(whs, key=lambda w: whs[w])] += extra
    print(f"over-shipped by packing warehouse: {dict(per_wh)}")
    for e in examples[:8]:
        print("  e.g.", e)


if __name__ == "__main__":
    main()
