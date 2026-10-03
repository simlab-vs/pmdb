#!/bin/sh
# Record arm B's trace of the failing production run (month-end run of 2026-09-30, 23:50 Europe/Berlin).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
# The points database as it was at 23:50 is in private/; the wall clock of that night is simulated by
# sim/sitecustomize.py (start 23:50:02 CEST, advancing with the job's own clock reads; the CRM accepts).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(cd "${1:-/work}" && pwd)
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/srv/loyalty/data" "$TMP/srv/loyalty/reports"
cp "$HERE/private/points-2026-09-30T2350.db" "$TMP/srv/loyalty/data/points.db"
cd "$WORK"
TZ=Europe/Berlin SIM_START=2026-09-30T23:50:02+02:00 SIM_STEP=0.048 SIM_ROOT="$WORK" \
  PYTHONPATH="$HERE/sim:$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" nightly.py \
  --db "$TMP/srv/loyalty/data/points.db" --out "$TMP/srv/loyalty/reports" 2>"$TMP/stderr" \
  || { cat "$TMP/stderr" >&2; exit 1; }
tail -n 1 "$TMP/stderr" >&2
