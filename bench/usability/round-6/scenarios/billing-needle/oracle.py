#!/usr/bin/env python3
"""Grade a billing-needle fix.

    python3 oracle.py <dir>        # <dir>: the agent's final /work
    python3 oracle.py --strict <dir>

Runs the agent's run_billing.py on hidden datasets and compares the bill
register and the summary with the reference fix's (hidden/<case>/expected):

* original: the reported September run (pristine copy of its data);
* h1: another legacy account, GridSense meter exchanged for a Meterline one;
* h2: a legacy Telemetrix->Meterline exchange plus a non-legacy
      GridSense->Meterline exchange (ids "AC123456" vs "AC-123456");
* h3 (required only with --strict): a legacy account whose closing read is
      delivered under its current id, so its two reads arrive under two ids
      out of time order.

Exit status 0 iff every required case matches.
"""

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
REQUIRED = ["original", "h1", "h2"]
STRICT = ["h3"]
PERIOD = "2026-09"


def read_bills(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["account"]: row for row in csv.DictReader(handle)}


def normalized_summary(path):
    return [" ".join(line.split()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_case(program, case, scratch):
    out = scratch / f"out_{case}"
    try:
        proc = subprocess.run(
            [sys.executable, "run_billing.py", "--period", PERIOD,
             "--data", str(HIDDEN / case / "data"), "--out", str(out)],
            cwd=program, capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "timed out"
    if proc.returncode != 0:
        return f"exit status {proc.returncode}: {proc.stderr.strip().splitlines()[-1:] }"
    expected_dir = HIDDEN / case / "expected"
    try:
        got = read_bills(out / f"bills_{PERIOD}.csv")
        got_summary = normalized_summary(out / f"summary_{PERIOD}.txt")
    except (OSError, KeyError) as exc:
        return f"missing or malformed output: {exc}"
    want = read_bills(expected_dir / f"bills_{PERIOD}.csv")
    if set(got) != set(want):
        missing = sorted(set(want) - set(got))[:5]
        extra = sorted(set(got) - set(want))[:5]
        return f"bill accounts differ (missing {missing}, unexpected {extra})"
    wrong = [account for account in sorted(want) if got[account] != want[account]]
    if wrong:
        account = wrong[0]
        return f"{len(wrong)} bill(s) differ, e.g. {account}: got {dict(got[account])}, want {dict(want[account])}"
    if got_summary != normalized_summary(expected_dir / f"summary_{PERIOD}.txt"):
        return "summary differs"
    return None


def main(argv):
    strict = "--strict" in argv
    args = [arg for arg in argv if arg != "--strict"]
    if len(args) != 1:
        print(__doc__)
        return 2
    source = Path(args[0]).resolve()
    with tempfile.TemporaryDirectory(prefix="oracle-billing-") as tmp:
        scratch = Path(tmp)
        program = scratch / "program"
        shutil.copytree(source, program, ignore=shutil.ignore_patterns(
            "data", "out", "*.pmdb", "__pycache__", ".git"))
        failures = []
        for case in REQUIRED + STRICT:
            problem = run_case(program, case, scratch)
            required = case in REQUIRED or strict
            status = "ok" if problem is None else ("FAIL" if required else "fail (not required)")
            print(f"  {case}: {status}" + ("" if problem is None else f": {problem}"))
            if problem is not None and required:
                failures.append(case)
    if failures:
        print(f"FAIL: {', '.join(failures)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
