#!/bin/sh
# Record arm B's trace of the reported run: python3 run_billing.py --period 2026-09 --data data --out out
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else in WORKDIR.
set -e
WORKDIR=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"; find "$WORKDIR" -name __pycache__ -type d -prune -exec rm -rf {} +' EXIT
cd "$WORKDIR"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORKDIR/report.pmdb" \
  run_billing.py --period 2026-09 --data data --out "$OUT" > "$OUT/stdout.txt" 2> "$OUT/stderr.txt"
