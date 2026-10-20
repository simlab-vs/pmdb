#!/usr/bin/env bash
# Records arm B's trace of the failing run: record.sh [WORKDIR] (default /work).
# Writes WORKDIR/report.pmdb and nothing else in WORKDIR (outputs go to a temporary directory).
# Expected: about 3 minutes (as long as a plain run), ~520k observations, ~85 MB.
set -euo pipefail
WORK="${1:-/work}"
SKILL="${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}"
PMDB_PYTHONPATH="${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
cd "$WORK"
status=0
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" \
  plan_day.py data/orders_2026-09-28.json --fleet data/fleet.json -o "$OUT/out" \
  > "$OUT/stdout" 2> "$OUT/stderr" || status=$?
tail -n 3 "$OUT/stderr" >&2
grep -A2 '^problems' "$OUT/stdout" >&2 || true
# The failing run exits 1 (the plan has a problem); anything else is unexpected.
[ "$status" -eq 1 ] || { echo "record.sh: unexpected exit status $status" >&2; exit 1; }
[ -s "$WORK/report.pmdb" ]
