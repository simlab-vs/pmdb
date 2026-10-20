#!/bin/sh
# Record arm B's trace of the failing production payroll run (September 2026, private HR export).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The export lives where production keeps it; its path (not the scenario's) is what the trace shows.
mkdir -p "$TMP/srv/payroll/in" "$TMP/srv/payroll/out" "$TMP/srv/payroll/reports"
cp "$HERE/private/hr-2026-09.json" "$TMP/srv/payroll/in/"
cd "$WORK"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" run_payroll.py \
  --hr-export "$TMP/srv/payroll/in/hr-2026-09.json" --period 2026-09 \
  --out "$TMP/srv/payroll/reports" --bank-out "$TMP/srv/payroll/out" 2>"$TMP/stderr" \
  || { cat "$TMP/stderr" >&2; exit 1; }
tail -n 1 "$TMP/stderr" >&2
