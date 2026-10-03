#!/usr/bin/env python3
"""Grade a stock-allocation fix: python3 oracle.py <agent's /work>.

Runs the agent's allocation job on hidden nights (the failing night's orders
and inventory levels, plus three others) and compares what the pick lists
send to each warehouse, and what the summary backorders, with an
independent reference allocation of the documented policy
(gen/reference.py). It also reports invariant violations: pick rows that ask
a warehouse for more units than it had, or a line for more than was ordered.
Exit 0 = PASS, 1 = FAIL.
"""

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
DAY = "2026-09-29"
DATASETS = [
    ("h1-original", "the failing night of 29 September"),
    ("h2-low-stock", "many SKU locations below their safety stock"),
    ("h3-marketplace-kits", "mostly marketplace orders, many kits and express orders"),
    ("h4-ample-stock", "ample stock, nothing below safety stock (regression check)"),
]
UNAVAILABLE = {"counting", "blocked", "quarantine"}


def run_one(work, name):
    data = HIDDEN / name
    truth = json.loads((data / "truth.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        out, reports = Path(tmp) / "out", Path(tmp) / "reports"
        proc = subprocess.run(
            [sys.executable, "allocate_night.py", "--orders", str(data / "orders.jsonl"), "--date", DAY,
             "--levels-file", str(data / "levels.json"), "--out", str(out), "--reports", str(reports)],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return [f"exit status {proc.returncode}: {proc.stderr.strip().splitlines()[-1:]}"]
        shipped = Counter()
        for path in sorted(out.glob(f"pick-*-{DAY}.csv")):
            warehouse = path.name.split("-")[1]
            with open(path, newline="") as handle:
                for row in csv.DictReader(handle):
                    shipped[(row["order_id"], int(row["line_no"]), row["sku"], warehouse)] += int(row["qty"])
        summary_path = reports / f"allocation-{DAY}.json"
        if not summary_path.exists():
            return ["no JSON summary written"]
        summary = json.loads(summary_path.read_text())
    backorders = Counter()
    for item in summary.get("backorders", []):
        backorders[(item["order_id"], int(item["line_no"]))] += int(item["qty"])

    problems = []
    physical = {}
    for r in json.loads((data / "levels.json").read_text())["levels"]:
        free = 0 if r.get("status") in UNAVAILABLE else max(0, r["on_hand"] - r["reserved"])
        physical[(r["sku"], r["warehouse"])] = free
    per_location = Counter()
    for (order_id, line_no, sku, warehouse), qty in shipped.items():
        if qty <= 0:
            problems.append(f"pick row {order_id}/{line_no} {sku} @ {warehouse} has quantity {qty}")
        per_location[(sku, warehouse)] += qty
    over = {k: (q, physical.get(k, 0)) for k, q in per_location.items() if q > physical.get(k, 0)}
    if over:
        units = sum(q - p for q, p in over.values())
        problems.append(f"{len(over)} SKU locations picked beyond their stock ({units} units short), e.g. "
                        + ", ".join(f"{s}@{w}: {q} > {p}" for (s, w), (q, p) in list(over.items())[:3]))

    expected = Counter({(o, l, s, w): q for o, l, s, w, q in truth["shipped"]})
    expected_back = Counter({(o, l): q for o, l, q in truth["backorders"]})
    wrong_lines = defaultdict(list)
    for key in set(expected) | set(shipped):
        if expected[key] != shipped[key]:
            wrong_lines[key[:2]].append(f"{key[2]}@{key[3]} {shipped[key]} (expected {expected[key]})")
    for key in set(expected_back) | set(backorders):
        if expected_back[key] != backorders[key]:
            wrong_lines[key].append(f"backordered {backorders[key]} (expected {expected_back[key]})")
    if wrong_lines:
        sample = list(wrong_lines.items())[:4]
        problems.append(f"{len(wrong_lines)} order lines allocated differently from the policy, e.g. "
                        + "; ".join(f"{o}/{l}: {', '.join(d)}" for (o, l), d in sample))
    return problems


def main():
    if len(sys.argv) != 2:
        print("usage: oracle.py <work dir>")
        return 2
    source = Path(sys.argv[1]).resolve()
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(source, work, ignore=shutil.ignore_patterns("__pycache__", "*.pmdb", "out"))
        for name, what in DATASETS:
            try:
                problems = run_one(work, name)
            except subprocess.TimeoutExpired:
                problems = ["timed out"]
            if problems:
                failures.append(f"{name} ({what}):\n    " + "\n    ".join(problems))
    if failures:
        print("FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print(f"PASS ({len(DATASETS)} nights allocated as the policy says)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
