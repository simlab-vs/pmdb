#!/usr/bin/env python3
"""Generate the catalog, a night's open orders and the inventory levels.

  gen_data.py --catalog-out ../work/catalog            (catalog only, fixed seed)
  gen_data.py --seed S --orders-out O.jsonl --levels-out L.json [options]

The catalog must exist (read from --catalog) before orders/levels are generated.
"""

import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

WAREHOUSES = ["LEE", "RTM", "LEJ", "MAD"]
STOCK_SHARE = {"LEE": 0.62, "RTM": 0.86, "LEJ": 0.86, "MAD": 0.45}
FAMILIES = [
    ("KT", "Kitchen", ["pan", "knife", "board", "kettle", "grater", "whisk", "mug", "jar"]),
    ("HM", "Home", ["cushion", "throw", "frame", "vase", "clock", "basket", "rug", "hook"]),
    ("GD", "Garden", ["hose", "trowel", "planter", "lantern", "shears", "seed tray", "bench", "parasol"]),
    ("BT", "Bath", ["towel", "mat", "dispenser", "caddy", "mirror", "robe", "rack", "tumbler"]),
    ("LT", "Lighting", ["lamp", "bulb", "shade", "string lights", "spot", "lamp oil", "candle", "dimmer"]),
    ("TL", "Tools", ["drill bits", "spirit level", "toolbox", "glue", "tape", "solvent", "ladder", "saw"]),
]
HAZMAT_WORDS = {"lamp oil", "solvent", "glue"}
BULKY_WORDS = {"bench", "parasol", "ladder", "rug"}
COUNTRIES = [("DE", 30), ("GB", 16), ("FR", 12), ("NL", 8), ("BE", 4), ("AT", 5), ("ES", 7), ("IT", 6),
             ("PL", 4), ("IE", 2), ("DK", 2), ("CZ", 2), ("PT", 2)]


def make_catalog(out_dir, seed=4401):
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for prefix, family, words in FAMILIES:
        for number in range(150):
            word = words[number % len(words)]
            variant = rng.choice(["", " small", " large", " grey", " oak", " white", " black", " set of 2"])
            rows.append({
                "sku": f"{prefix}-{1000 + number}",
                "name": f"{family} {word}{variant}",
                "hazmat": "1" if word in HAZMAT_WORDS else "0",
                "bulky": "1" if word in BULKY_WORDS else "0",
                "active": "1",
            })
    kits = []
    plain = [r["sku"] for r in rows if r["hazmat"] == "0" and r["bulky"] == "0"]
    for number in range(24):
        kit = f"KIT-{2000 + number}"
        parts = rng.sample(plain[:300], rng.choice([2, 2, 3]))
        rows.append({"sku": kit, "name": f"Bundle {number + 1}", "hazmat": "0", "bulky": "0", "active": "1"})
        for part in parts:
            kits.append({"kit": kit, "component": part, "qty": str(rng.choice([1, 1, 2]))})
    with open(out_dir / "skus.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, ["sku", "name", "hazmat", "bulky", "active"])
        writer.writeheader()
        writer.writerows(rows)
    with open(out_dir / "kits.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, ["kit", "component", "qty"])
        writer.writeheader()
        writer.writerows(kits)


def read_catalog(directory):
    directory = Path(directory)
    with open(directory / "skus.csv") as handle:
        skus = list(csv.DictReader(handle))
    kits = {}
    with open(directory / "kits.csv") as handle:
        for row in csv.DictReader(handle):
            kits.setdefault(row["kit"], []).append((row["component"], int(row["qty"])))
    return skus, kits


def popularity(rng, skus):
    order = [s["sku"] for s in skus if not s["sku"].startswith("KIT-")]
    rng.shuffle(order)
    return {sku: 1.0 / (rank + 3) ** 0.9 for rank, sku in enumerate(order)}


def make_levels(rng, skus, pop, args):
    levels = []
    low = 0
    for row in skus:
        sku = row["sku"]
        if sku.startswith("KIT-"):
            continue
        weight = pop[sku]
        for warehouse in WAREHOUSES:
            if warehouse == "MAD" and (row["hazmat"] == "1" or row["bulky"] == "1"):
                continue
            share = STOCK_SHARE[warehouse] + (0.12 if weight > 0.02 else 0)
            if rng.random() > share:
                continue
            fast = weight > 0.01
            safety = rng.choice([4, 5, 6, 8, 10, 12]) if fast else rng.choice([0, 0, 2, 2, 3, 4])
            base = int(rng.uniform(0.2, 2.2) * weight * args.stock_scale) + rng.randint(2, 14)
            reserved = rng.choice([0, 0, 0, 1, 2, 3, 5])
            available = base
            if safety > 0 and rng.random() < args.p_low:
                available = rng.randint(0, safety - 1)
                low += 1
            on_hand = available + reserved
            if rng.random() < args.p_oversold:
                on_hand = max(0, reserved - rng.randint(1, 3))
            status = "active"
            draw = rng.random()
            if draw < 0.008 * args.status_scale:
                status = "counting"
            elif draw < 0.011 * args.status_scale:
                status = "blocked"
            aisle = {"LEE": "A", "RTM": "R", "LEJ": "L", "MAD": "M"}[warehouse]
            levels.append({
                "sku": sku, "warehouse": warehouse, "on_hand": on_hand, "reserved": reserved,
                "safety_stock": safety, "bin": f"{aisle}-{rng.randint(1, 48):02d}-{rng.randint(1, 9):02d}",
                "status": status,
            })
    rng.shuffle(levels)
    levels.sort(key=lambda r: (r["warehouse"], r["sku"]))
    return levels, low


def make_orders(rng, skus, kits, pop, args):
    plain = list(pop)
    weights = [pop[s] for s in plain]
    kit_ids = sorted(kits)
    countries = [c for c, _ in COUNTRIES]
    cweights = [w for _, w in COUNTRIES]
    start = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc) - timedelta(hours=args.backlog_hours)
    end = datetime(2026, 9, 29, 1, 58, tzinfo=timezone.utc)
    span = (end - start).total_seconds()
    orders = []
    packs = {}
    numbers = {"web": 3104200, "marketplace": 881300, "b2b": 51200}
    for _ in range(args.orders):
        channel = rng.choices(["web", "marketplace", "b2b"], [args.w_web, args.w_mp, args.w_b2b])[0]
        numbers[channel] += rng.randint(1, 9)
        prefix = {"web": "W", "marketplace": "M", "b2b": "B"}[channel]
        created = start + timedelta(seconds=rng.uniform(0, span))
        n_lines = rng.choices([1, 2, 3, 4], [55, 25, 12, 8])[0] if channel != "b2b" else rng.choice([1, 2, 3, 4, 5])
        lines = []
        used = set()
        for line_no in range(1, n_lines + 1):
            if channel != "b2b" and rng.random() < args.p_kit:
                sku = rng.choice(kit_ids)
            else:
                sku = rng.choices(plain, weights)[0]
            if sku in used:
                continue
            used.add(sku)
            if channel == "b2b":
                qty = rng.choice([6, 6, 8, 10, 12, 12, 18, 24])
            else:
                qty = rng.choices([1, 2, 3, 4, 6], [62, 22, 9, 5, 2])[0]
            status = "open" if rng.random() > 0.01 else "cancelled"
            line = {"line_no": line_no, "sku": sku, "qty": qty, "status": status}
            if channel == "marketplace":
                line["pack_size"] = packs.setdefault(sku, rng.choices([1, 2, 3], [85, 10, 5])[0])
                if line["pack_size"] > 1:
                    line["qty"] = rng.choice([1, 1, 2])
            lines.append(line)
        order = {
            "order_id": f"{prefix}-{numbers[channel]}",
            "channel": channel,
            "service": "express" if channel != "b2b" and rng.random() < args.p_express else "standard",
            "country": rng.choices(countries, cweights)[0],
            "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ship_complete": channel == "b2b" and rng.random() < 0.85,
            "hold": rng.random() < 0.015,
            "lines": lines,
        }
        orders.append(order)
    orders.sort(key=lambda o: o["created_at"])
    return orders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-out")
    parser.add_argument("--catalog", default=str(Path(__file__).resolve().parent.parent / "work" / "catalog"))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--orders-out")
    parser.add_argument("--levels-out")
    parser.add_argument("--orders", type=int, default=2700)
    parser.add_argument("--p-low", type=float, default=0.06)
    parser.add_argument("--stock-scale", type=float, default=600)
    parser.add_argument("--w-web", type=float, default=0.55)
    parser.add_argument("--w-mp", type=float, default=0.32)
    parser.add_argument("--w-b2b", type=float, default=0.13)
    parser.add_argument("--p-kit", type=float, default=0.03)
    parser.add_argument("--p-express", type=float, default=0.22)
    parser.add_argument("--p-oversold", type=float, default=0.01)
    parser.add_argument("--status-scale", type=float, default=1.0)
    parser.add_argument("--backlog-hours", type=float, default=6)
    parser.add_argument("--generated-at", default="2026-09-29T02:00:04Z")
    args = parser.parse_args()
    if args.catalog_out:
        make_catalog(args.catalog_out)
        return
    rng = random.Random(args.seed)
    skus, kits = read_catalog(args.catalog)
    pop = popularity(rng, skus)
    levels, low = make_levels(rng, skus, pop, args)
    orders = make_orders(rng, skus, kits, pop, args)
    with open(args.orders_out, "w") as handle:
        for order in orders:
            handle.write(json.dumps(order, separators=(",", ":")) + "\n")
    with open(args.levels_out, "w") as handle:
        json.dump({"generated_at": args.generated_at, "levels": levels}, handle, separators=(",", ":"))
    print(f"{len(orders)} orders, {sum(len(o['lines']) for o in orders)} lines, {len(levels)} levels, {low} below safety stock")


if __name__ == "__main__":
    main()
