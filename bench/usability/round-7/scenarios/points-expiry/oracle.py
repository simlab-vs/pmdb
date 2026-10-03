#!/usr/bin/env python3
"""Grade a points-expiry fix: python3 oracle.py <agent's /work>.

Runs the agent's nightly job on hidden points databases under a simulated
wall clock (sim/sitecustomize.py: the run starts at a given instant and the
clock advances with the job's own clock reads), and compares its report
(reports/nightly-<date>.json) with the truth computed independently by the
generator (gen/gen_db.py). Exit 0 = PASS, 1 = FAIL.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
SIM = HERE / "sim"
# name, database, truth, simulated start, clock step, what it checks
CASES = [
    ("h1-original", "h1-original", "2026-09-30T23:50:02+02:00", "0.048",
     "the failing month-end run of 2026-09-30, crossing midnight"),
    ("h1-late-start", "h1-original", "2026-09-30T23:59:30+02:00", "0.048",
     "the same database, started 30 s before midnight"),
    ("h2-october-cet", "h2-october-cet", "2026-10-31T23:50:02+01:00", "0.048",
     "month end of October (CET, 31 days), crossing midnight"),
    ("h3-quick-month-end", "h3-quick-month-end", "2026-08-31T23:50:02+02:00", "0.012",
     "month end finishing before midnight (regression)"),
    ("h4-daily-crossing", "h4-daily-crossing", "2026-09-29T23:58:30+02:00", "0.048",
     "daily run of 2026-09-29 crossing into the month's last day (no expiry)"),
]


def compare(expected, actual, path, problems):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            problems.append(f"{path} = {actual!r} (expected {expected!r})")
            return
        for key, value in expected.items():
            compare(value, actual.get(key), f"{path}.{key}" if path else key, problems)
        if path.endswith("expired_by_source"):
            extra = {k: v for k, v in actual.items() if k not in expected and v}
            if extra:
                problems.append(f"{path} has {extra} (expected {expected!r})")
        return
    if path.endswith("value_eur"):
        try:
            same = Decimal(str(actual)) == Decimal(str(expected))
        except Exception:
            same = False
    else:
        same = actual == expected
    if not same:
        problems.append(f"{path} = {actual!r} (expected {expected!r})")


def start(work, tmp, name, db, sim_start, step):
    case = Path(tmp) / name
    case.mkdir()
    shutil.copy(HIDDEN / f"{db}.db", case / "points.db")
    env = dict(os.environ)
    env.update({
        "TZ": "Europe/Berlin",
        "SIM_START": sim_start,
        "SIM_STEP": step,
        "SIM_ROOT": str(work),
        "PYTHONPATH": str(SIM),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return subprocess.Popen(
        [sys.executable, "nightly.py", "--db", str(case / "points.db"), "--out", str(case / "reports")],
        cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def grade(proc, tmp, name, db):
    try:
        _, stderr = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        return "timed out"
    if proc.returncode != 0:
        return f"exit status {proc.returncode}: {stderr.strip().splitlines()[-1:]}"
    truth = json.loads((HIDDEN / f"{db}.truth.json").read_text())
    report = Path(tmp) / name / "reports" / f"nightly-{truth['business_date']}.json"
    if not report.exists():
        return f"no report {report.name} written"
    actual = json.loads(report.read_text())
    problems = []
    compare(truth, actual, "", problems)
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
        work = work.resolve()
        procs = [(name, db, what, start(work, tmp, name, db, sim_start, step))
                 for name, db, sim_start, step, what in CASES]
        for name, db, what, proc in procs:
            problem = grade(proc, tmp, name, db)
            if problem:
                failures.append(f"{name} ({what}): {problem}")
    if failures:
        print("FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print(f"PASS ({len(CASES)} runs match the truth)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
