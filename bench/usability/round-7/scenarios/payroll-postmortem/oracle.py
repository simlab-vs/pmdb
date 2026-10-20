#!/usr/bin/env python3
"""Grade a payroll-postmortem fix: python3 oracle.py <agent's /work>.

Runs the agent's payroll job on hidden HR exports (the original private one
and three new ones) and compares the per-cost-centre and total figures of its
JSON register with HR's own calculation, computed independently by the
generator (``*.truth.json``). Exit 0 = PASS, 1 = FAIL.
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
    ("h1-original", "the September export of the failing run"),
    ("h2-many-gaps", "many breaks between assignment rows: inside the month, at its start and end, across it"),
    ("h3-hourly-gaps", "breaks between assignment rows, mostly of hourly staff"),
    ("h4-contiguous", "no break between rows in the month (regression check)"),
]


def run_one(work, name):
    truth = json.loads((HIDDEN / f"{name}.truth.json").read_text())["truth"]
    with tempfile.TemporaryDirectory() as out:
        proc = subprocess.run(
            [sys.executable, "run_payroll.py", "--hr-export", str(HIDDEN / f"{name}.json"), "--period", "2026-09",
             "--out", out, "--bank-out", out],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return f"exit status {proc.returncode}: {proc.stderr.strip().splitlines()[-1:]}"
        report = Path(out) / "payroll-register-2026-09.json"
        if not report.exists():
            return "no JSON register written"
        got = json.loads(report.read_text())
    problems = []
    for column, value in truth["totals"].items():
        actual = got.get("totals", {}).get(column)
        if actual != value:
            problems.append(f"total {column} = {actual} (expected {value})")
    for code, row in truth["cost_centres"].items():
        for column, value in row.items():
            actual = got.get("cost_centres", {}).get(code, {}).get(column)
            if actual != value:
                problems.append(f"{code}.{column} = {actual} (expected {value})")
    if len(problems) > 6:
        problems = problems[:6] + [f"... {len(problems) - 6} more"]
    return "; ".join(problems)


def main():
    if len(sys.argv) != 2:
        print("usage: oracle.py <work dir>")
        return 2
    source = Path(sys.argv[1]).resolve()
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(source, work, ignore=shutil.ignore_patterns("__pycache__", "*.pmdb"))
        for name, what in DATASETS:
            try:
                problem = run_one(work, name)
            except subprocess.TimeoutExpired:
                problem = "timed out"
            if problem:
                failures.append(f"{name} ({what}): {problem}")
    if failures:
        print("FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print(f"PASS ({len(DATASETS)} exports match HR's calculation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
