#!/bin/sh
# Record arm B's trace of the failing production run (business date 2026-09-28; the queue messages are gone).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The run is replayed from the queue's messages as received (a dump kept for this recording only).
mkdir -p "$TMP/spool" "$TMP/reports"
cp "$HERE/private/card-events-2026-09-28.jsonl.gz" "$TMP/spool/"
cd "$WORK"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" run_ledger.py \
  --business-date 2026-09-28 --spool "$TMP/spool/card-events-2026-09-28.jsonl.gz" --out "$TMP/reports" 2>"$TMP/stderr" \
  || { cat "$TMP/stderr" >&2; exit 1; }
tail -n 1 "$TMP/stderr" >&2
