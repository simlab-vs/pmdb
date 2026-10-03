#!/usr/bin/env python3
"""Grade a refund-postmortem fix: python3 oracle.py <agent's /work>.

Runs the agent's job on hidden exports (the original private one and three
new ones) and compares the per-provider totals of its JSON report with the
providers' statements (refunds counted once, at their final status, only if
it is succeeded). Exit 0 = PASS, 1 = FAIL.
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
    ("h1-original", "the failing September export"),
    ("h2-all-migrated", "every NovaPay account on API 2026-08-01, many reversals and partial refunds"),
    ("h3-processing", "refunds passing through a processing status"),
    ("h4-legacy-only", "no account on the new API (regression check)"),
]


def run_one(work, name):
    export = HIDDEN / f"{name}.jsonl.gz"
    truth = json.loads((HIDDEN / f"{name}.jsonl.gz.truth.json").read_text())["truth"]
    with tempfile.TemporaryDirectory() as out:
        proc = subprocess.run(
            [sys.executable, "monthly_report.py", "--export", str(export), "--month", "2026-09", "--out", out],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return f"exit status {proc.returncode}: {proc.stderr.strip().splitlines()[-1:]}"
        report = Path(out) / "payout-recon-2026-09.json"
        if not report.exists():
            return "no JSON report written"
        got = json.loads(report.read_text()).get("providers", {})
    problems = []
    for provider, expected in truth.items():
        actual = got.get(provider, {})
        for column, value in expected.items():
            if actual.get(column) != value:
                problems.append(f"{provider}.{column} = {actual.get(column)} (expected {value})")
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
    print(f"PASS ({len(DATASETS)} exports reconcile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
