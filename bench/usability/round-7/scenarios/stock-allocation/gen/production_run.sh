#!/bin/sh
# Run the job on WORKDIR as cron did on 29 September (inventory service answered from the private
# snapshot) and write its log and summary, rewritten to production paths and times, into OUTDIR:
#   production_run.sh WORKDIR OUTDIR
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(cd "$1" && pwd)
OUT=$2
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT/logs" "$OUT/reports"
(cd "$WORK" && PYTHONPATH="$HERE/service" INVENTORY_SNAPSHOT="$HERE/../private/levels-2026-09-29T0200.json" \
  PYTHONDONTWRITEBYTECODE=1 python3 allocate_night.py --orders input/orders-2026-09-29.jsonl --date 2026-09-29 \
  --out "$TMP/out" --reports "$TMP/reports" --log "$TMP/log" 2>/dev/null)
python3 - "$TMP" "$OUT" <<'PYEOF'
import json, re, sys
from datetime import datetime, timedelta
tmp, out = sys.argv[1:3]
paths = [(f"{tmp}/out", "/srv/allocation/out"), (f"{tmp}/reports", "/srv/allocation/reports"),
         ("input/orders-2026-09-29.jsonl", "/srv/oms/exports/open-lines-2026-09-29.jsonl")]
base = datetime(2026, 9, 29, 2, 0, 3, 412000)
first = None
lines = []
for line in open(f"{tmp}/log"):
    stamp = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
    first = first or stamp
    when = base + (stamp - first)
    text = line[23:]
    for old, new in paths:
        text = text.replace(old, new)
    lines.append(when.strftime("%Y-%m-%d %H:%M:%S,") + f"{when.microsecond // 1000:03d}" + text)
open(f"{out}/logs/allocation-2026-09-29.log", "w").writelines(lines)
generated = "2026-09-29T00:00:04Z"
txt = open(f"{tmp}/reports/allocation-2026-09-29.txt").read()
txt = re.sub(r"Generated: \S+", f"Generated: {generated}", txt)
open(f"{out}/reports/allocation-2026-09-29.txt", "w").write(txt)
body = json.load(open(f"{tmp}/reports/allocation-2026-09-29.json"))
body["generated_at"] = generated
with open(f"{out}/reports/allocation-2026-09-29.json", "w") as handle:
    json.dump(body, handle, indent=1, sort_keys=True)
PYEOF
