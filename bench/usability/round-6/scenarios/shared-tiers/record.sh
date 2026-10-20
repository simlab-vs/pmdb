#!/usr/bin/env bash
# Record arm B's trace of the failing run (the command in issue.md) into WORKDIR/report.pmdb.
# Usage: record.sh [WORKDIR]   (default /work). Outputs go to a temp dir, so WORKDIR gains
# report.pmdb only.
set -euo pipefail
WORKDIR="${1:-/work}"
SKILL="${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}"
PMDB_PYTHONPATH="${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
cd "$WORKDIR"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PMDB_PYTHONPATH" \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORKDIR/report.pmdb" \
  run_invoices.py data --period 2026-09 --out "$OUT/out"
