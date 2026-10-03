#!/usr/bin/env python3
"""Reference allocation, written independently of the job, from its documented policy.

  reference.py ORDERS.jsonl LEVELS.json SETTINGS.toml CATALOG_DIR > TRUTH.json

Policy (README and settings): lines in order (express first, then created_at,
order id, line no); each line's warehouses follow the destination country's
route, keeping those that can handle every part (hazmat/bulky) and stock it;
a location's stock is on hand minus reserved, at least 0, and 0 while it is
under count, blocked or in quarantine; marketplace lines can't take a
location's safety stock; kits and ship-complete lines come from one warehouse
that can fill them; other lines take what they can from each warehouse in turn.
The truth lists every shipped unit per (order, line, sku, warehouse) and the
backordered units per line.
"""

import csv
import json
import sys
import tomllib
from collections import defaultdict


def main():
    orders_path, levels_path, settings_path, catalog_dir = sys.argv[1:5]
    settings = tomllib.load(open(settings_path, "rb"))
    whs = settings["warehouses"]
    routes = {}
    for countries, seq in settings["routing"]["routes"].items():
        for c in countries.split(","):
            routes[c.strip()] = seq
    default = settings["routing"]["default"]
    protected = set(settings["policy"]["protect_safety_stock_from"])
    express_first = settings["policy"].get("express_first", True)

    skus = {}
    with open(f"{catalog_dir}/skus.csv") as h:
        for r in csv.DictReader(h):
            skus[r["sku"]] = (r["hazmat"] == "1", r["bulky"] == "1")
    kits = defaultdict(list)
    with open(f"{catalog_dir}/kits.csv") as h:
        for r in csv.DictReader(h):
            kits[r["kit"]].append((r["component"], int(r["qty"])))

    stock, safety = {}, {}
    for r in json.load(open(levels_path))["levels"]:
        if r["warehouse"] not in whs or r["sku"] not in skus or r["sku"] in kits:
            continue
        free = max(0, int(r["on_hand"]) - int(r["reserved"]))
        if r.get("status", "active") in ("counting", "blocked", "quarantine"):
            free = 0
        stock[(r["sku"], r["warehouse"])] = free
        safety[(r["sku"], r["warehouse"])] = max(0, int(r.get("safety_stock", 0)))

    lines, seen = [], set()
    for text in open(orders_path):
        if not text.strip():
            continue
        o = json.loads(text)
        if o.get("hold") or o.get("channel") not in ("web", "marketplace", "b2b"):
            continue
        service = o.get("service", "standard")
        if service not in ("express", "standard"):
            service = "standard"
        for l in o.get("lines", ()):
            key = (o["order_id"], int(l["line_no"]))
            if key in seen:
                continue
            seen.add(key)
            units = int(l["qty"]) * int(l.get("pack_size", 1))
            if l.get("status", "open") != "open" or l["sku"] not in skus or units <= 0:
                continue
            rank = 0 if express_first and service == "express" else 1
            lines.append(((rank, o["created_at"], o["order_id"], int(l["line_no"])),
                          o["order_id"], int(l["line_no"]), l["sku"], units, o["channel"],
                          o.get("country", "").upper(), bool(o.get("ship_complete", False))))
    lines.sort(key=lambda x: x[0])

    def usable(sku, wh, channel):
        free = stock.get((sku, wh), 0)
        if channel in protected:
            free -= safety.get((sku, wh), 0)
        return max(0, free)

    def handles(wh, sku):
        hazmat, bulky = skus[sku]
        return (not hazmat or whs[wh].get("hazmat", False)) and (not bulky or whs[wh].get("bulky", True))

    shipped, backorders = [], []
    for _, order_id, line_no, sku, qty, channel, country, complete in lines:
        parts = kits[sku] if sku in kits else [(sku, 1)]
        sources = [w for w in routes.get(country, default)
                   if all(handles(w, p) and (p, w) in stock for p, _ in parts)]
        if sku in kits or complete:
            for w in sources:
                if all(usable(p, w, channel) >= u * qty for p, u in parts):
                    for p, u in parts:
                        stock[(p, w)] -= u * qty
                        shipped.append([order_id, line_no, p, w, u * qty])
                    break
            else:
                backorders.append([order_id, line_no, qty])
            continue
        need = qty
        for w in sources:
            take = min(need, usable(sku, w, channel))
            if take > 0:
                stock[(sku, w)] -= take
                shipped.append([order_id, line_no, sku, w, take])
                need -= take
            if need == 0:
                break
        if need:
            backorders.append([order_id, line_no, need])
    json.dump({"shipped": shipped, "backorders": backorders}, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
