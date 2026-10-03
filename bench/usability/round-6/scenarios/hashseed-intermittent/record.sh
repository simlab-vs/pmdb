#!/usr/bin/env bash
# Record arm B's trace of the failing nightly build: report.pmdb in WORKDIR.
# The nightly ran `python3 build.py site --out public` with a random hash seed;
# the failing run is reproduced with PYTHONHASHSEED=316 (one of the ~7.6% of
# seeds for which the build is broken). The agent isn't told the seed.
set -euo pipefail
WORKDIR=$(cd "${1:-/work}" && pwd)
SKILL=${SKILL:-/home/ambrus/pytrace-recorder/skills/pmdb}
PMDB_PYTHONPATH=${PMDB_PYTHONPATH:-/home/ambrus/pytrace-recorder/Python}
cd "$WORKDIR"
if [ -e public ]; then
  echo "record.sh: $WORKDIR/public already exists" >&2
  exit 1
fi
status=0
PYTHONHASHSEED=316 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PMDB_PYTHONPATH" \
  python3 "$SKILL/scripts/pmdb-record" -o "$WORKDIR/report.pmdb" build.py site --out public || status=$?
rm -rf public
exit $status
