#!/bin/sh
# Record arm B's trace of the reported run:
#   python3 quote_run.py data --date 2026-09-30 --out out
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
# Expected: ~375k observations, ~47 MB, ~13 s.
set -e
WORKDIR=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
cd "$WORKDIR"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORKDIR/report.pmdb" \
  quote_run.py data --date 2026-09-30 --out "$OUT/out" > "$OUT/stdout.txt" 2> "$OUT/stderr.txt"
