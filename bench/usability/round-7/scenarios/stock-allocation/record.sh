#!/bin/sh
# Record arm B's trace of the failing production run (29 September, 02:00).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
# The inventory service is answered from the private snapshot of its levels at 02:00 (gen/service),
# so the trace shows the job reading the production URL, as it did.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The orders export lives where the OMS drops it; its path (not the scenario's) is what the trace shows.
mkdir -p "$TMP/oms/exports" "$TMP/allocation/out" "$TMP/allocation/reports"
cp "$WORK/input/orders-2026-09-29.jsonl" "$TMP/oms/exports/open-lines-2026-09-29.jsonl"
cd "$WORK"
PYTHONPATH="$HERE/gen/service:$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  INVENTORY_SNAPSHOT="$HERE/private/levels-2026-09-29T0200.json" \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" allocate_night.py \
  --orders "$TMP/oms/exports/open-lines-2026-09-29.jsonl" --date 2026-09-29 \
  --out "$TMP/allocation/out" --reports "$TMP/allocation/reports" 2>"$TMP/stderr" \
  || { cat "$TMP/stderr" >&2; exit 1; }
tail -n 1 "$TMP/stderr" >&2
