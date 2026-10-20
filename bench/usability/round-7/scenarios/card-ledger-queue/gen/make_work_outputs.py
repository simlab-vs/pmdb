#!/usr/bin/env python3
"""Run the pristine job on the private dump and write work/logs and work/reports as production had them.

Timestamps are shifted to the production run (2026-09-29 04:10 UTC), the dump line (production read the
queue itself) is dropped, and output paths are rewritten to /srv/cardledger.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WORK = HERE / "work"
DATE = "2026-09-28"
START = datetime(2026, 9, 29, 4, 10, 2, 381000)

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    log = tmp / "run.log"
    subprocess.run([sys.executable, "run_ledger.py", "--business-date", DATE,
                    "--spool", str(HERE / "private" / f"card-events-{DATE}.jsonl.gz"),
                    "--out", str(tmp / "out"), "--log", str(log)],
                   cwd=WORK, check=True, capture_output=True, env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    lines = log.read_text().splitlines()
    first = None
    out = []
    for line in lines:
        if "from dump" in line:
            continue
        stamp = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
        first = first or stamp
        shifted = START + (stamp - first) * 40
        text = line[23:].replace(str(tmp / "out"), "/srv/cardledger/reports")
        out.append(shifted.strftime("%Y-%m-%d %H:%M:%S,") + f"{shifted.microsecond // 1000:03d}" + text)
    (WORK / "logs").mkdir(exist_ok=True)
    (WORK / "logs" / f"cardledger-{DATE}.log").write_text("\n".join(out) + "\n")
    (WORK / "reports").mkdir(exist_ok=True)
    shutil.copy(tmp / "out" / f"settlement-{DATE}.txt", WORK / "reports" / f"settlement-{DATE}.txt")
for p in WORK.rglob("__pycache__"):
    shutil.rmtree(p)
