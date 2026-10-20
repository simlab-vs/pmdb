#!/usr/bin/env python3
"""Grade a card-ledger-queue fix: python3 oracle.py <agent's /work>.

Runs the agent's ledger job on hidden queue dumps (the original consumed
queue and three new ones) and compares its settlement summary JSON with the
truth computed by the generator from the unique card events (what the
issuing bank settles): totals, counts, clearings per merchant group, and
every card's movement and held amount. Exit 0 = PASS, 1 = FAIL.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
DATASETS = [
    ("h1-original", "2026-09-28", "the consumed queue of the failing run"),
    ("h2-commuters", "2026-09-29", "many transit riders, tolls and parking; frequent processor re-sends"),
    ("h3-redelivery-storm", "2026-09-30", "heavy redelivery, re-sends often before the original, much reordering"),
    ("h4-no-identical-fares", "2026-09-27", "no two identical offline fares on a card (regression)"),
]


def compare(got, truth):
    problems = []
    for section in ("totals", "counts", "clearings_by_group"):
        actual = got.get(section, {})
        for key, value in truth[section].items():
            if actual.get(key) != value:
                problems.append(f"{section}.{key} = {actual.get(key)} (expected {value})")
    cards = got.get("cards", {})
    wrong = [card for card, value in truth["cards"].items() if cards.get(card) != value]
    extra = [card for card in cards if card not in truth["cards"]]
    if wrong or extra:
        problems.append(f"{len(wrong)} cards with a wrong movement or hold, {len(extra)} unexpected cards"
                        + (f", e.g. {wrong[0]}: {cards.get(wrong[0])} (expected {truth['cards'][wrong[0]]})" if wrong else ""))
    return problems


def run_one(work, name, date):
    dump = HIDDEN / f"{name}.jsonl.gz"
    truth = json.loads((HIDDEN / f"{name}.jsonl.gz.truth.json").read_text())["truth"]
    with tempfile.TemporaryDirectory() as out:
        proc = subprocess.run(
            [sys.executable, "run_ledger.py", "--business-date", date, "--spool", str(dump), "--out", out],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return [f"exit status {proc.returncode}: {proc.stderr.strip().splitlines()[-1:]}"]
        report = Path(out) / f"settlement-{date}.json"
        if not report.exists():
            return ["no settlement JSON written"]
        got = json.loads(report.read_text())
    return compare(got, truth)


def main():
    if len(sys.argv) != 2:
        print("usage: oracle.py <work dir>")
        return 2
    source = Path(sys.argv[1]).resolve()
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(source, work, ignore=shutil.ignore_patterns("__pycache__", "*.pmdb"))
        for name, date, what in DATASETS:
            try:
                problems = run_one(work, name, date)
            except subprocess.TimeoutExpired:
                problems = ["timed out"]
            if problems:
                failures.append(f"{name} ({what}):\n    " + "\n    ".join(problems[:8]))
    if failures:
        print("FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print(f"PASS ({len(DATASETS)} queue dumps settle)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
