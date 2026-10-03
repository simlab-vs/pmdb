#!/bin/sh
# Record arm B's trace of the failing production run (September export, private data).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else there.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The export lives where production keeps it; its path (not the scenario's) is what the trace shows.
mkdir -p "$TMP/exports" "$TMP/reports"
cp "$HERE/private/events-2026-09.jsonl.gz" "$TMP/exports/"
cd "$WORK"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORK/report.pmdb" monthly_report.py \
  --export "$TMP/exports/events-2026-09.jsonl.gz" --month 2026-09 --out "$TMP/reports" 2>"$TMP/stderr" \
  || { cat "$TMP/stderr" >&2; exit 1; }
tail -n 1 "$TMP/stderr" >&2
