#!/usr/bin/env python3
"""Grade a fix of bundle-memo.

python3 oracle.py DIR    (DIR: the agent's final /work)

Runs DIR's quote_run.py on the original data and on three hidden datasets
(other seeds and dates; one where BE and FR, not AT, have their own price
lists) and compares every row of quotes.csv with the reference fix's.
Exit 0 and PASS iff all match.
"""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HIDDEN = os.path.join(HERE, "hidden")


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def main():
    if len(sys.argv) != 2:
        print("usage: oracle.py DIR")
        return 2
    with open(os.path.join(HIDDEN, "datasets.json")) as f:
        datasets = json.load(f)
    with tempfile.TemporaryDirectory(prefix="oracle-bundle-memo-") as tmp:
        work = os.path.join(tmp, "work")
        shutil.copytree(sys.argv[1], work, ignore=shutil.ignore_patterns("__pycache__", "*.pmdb", ".git"))
        failures = []
        for ds in datasets:
            out = os.path.join(tmp, "out-" + ds["name"])
            try:
                proc = subprocess.run(
                    [sys.executable, "quote_run.py", os.path.join(HIDDEN, ds["name"]),
                     "--date", ds["date"], "--out", out],
                    cwd=work, capture_output=True, text=True, timeout=50,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0"),
                )
            except subprocess.TimeoutExpired:
                failures.append(f"{ds['name']}: timed out")
                continue
            if proc.returncode != 0:
                failures.append(f"{ds['name']}: exit {proc.returncode}: {proc.stderr.strip()[-300:]}")
                continue
            got = read(os.path.join(out, "quotes.csv"))
            want = read(os.path.join(HIDDEN, "expected", ds["name"] + ".csv"))
            wrong = [k for k in want if got.get(k) != want[k]]
            extra = [k for k in got if k not in want]
            if wrong or extra:
                sample = ", ".join(
                    f"{k}: {got.get(k, {}).get('total')} != {want[k]['total']}" for k in wrong[:3])
                failures.append(f"{ds['name']}: {len(wrong)} wrong quotes, {len(extra)} unexpected ({sample})")
        if failures:
            print("FAIL: " + "; ".join(failures))
            return 1
        print(f"PASS: all quotes match on {len(datasets)} datasets")
        return 0


if __name__ == "__main__":
    sys.exit(main())
