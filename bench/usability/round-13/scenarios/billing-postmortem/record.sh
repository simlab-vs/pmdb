#!/bin/sh
# Record the trace of the reported run (September extract, deleted after the run; kept in private/ for this only).
# Usage: record.sh [WORKDIR]   (default /work). Writes WORKDIR/report.pmdb and nothing else in WORKDIR.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORKDIR=${1:-/work}
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"; find "$WORKDIR" -name __pycache__ -type d -prune -exec rm -rf {} +' EXIT
# The extract lives where production keeps it; its path (not the scenario's) is what the trace shows.
mkdir -p "$TMP/srv/billing/extract" "$TMP/srv/billing/out"
cp -r "$HERE/private/extract-2026-09" "$TMP/srv/billing/extract/2026-09"
cd "$WORKDIR"
PYTHONPATH="$PMDB_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORKDIR/report.pmdb" \
  run_billing.py --period 2026-09 --data "$TMP/srv/billing/extract/2026-09" --out "$TMP/srv/billing/out" \
  > "$TMP/stdout.txt" 2> "$TMP/stderr.txt" || { cat "$TMP/stderr.txt" >&2; exit 1; }
tail -n 1 "$TMP/stderr.txt" >&2
