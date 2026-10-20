#!/usr/bin/env bash
# Validate the shared-tiers scenario on temp copies. Exit 0 iff every step passes.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PMDB="${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-5/_work/opt-pmdb/bin/pmdb}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
invoice() { python3 -c "import json,sys
for l in open(sys.argv[1]):
    i=json.loads(l)
    if i['number']==sys.argv[2]: print([x['amount'] for x in i['lines'] if x['code']=='api_requests'][0])" "$@"; }

cp -r "$HERE/work" "$T/pristine"
(cd "$T/pristine" && PYTHONDONTWRITEBYTECODE=1 python3 run_invoices.py data --period 2026-09 --out "$T/out-bug" >/dev/null 2>&1)
a=$(invoice "$T/out-bug/invoices.jsonl" INV-2026-09-1047); b=$(invoice "$T/out-bug/invoices.jsonl" INV-2026-09-0263)
[ "$a" = 2192.01 ] && [ "$b" = 1405.38 ]; step "1 failing run shows the symptom (INV-1047 API line $a, INV-0263 $b)" $?

python3 "$HERE/oracle.py" "$T/pristine" > "$T/o1" 2>&1; rc=$?; [ $rc = 1 ]; step "2 oracle fails on pristine work: $(cat "$T/o1")" $?

cp -r "$HERE/work" "$T/fixed" && patch -s -p1 -d "$T/fixed" < "$HERE/fix.patch"
(cd "$T/fixed" && PYTHONDONTWRITEBYTECODE=1 python3 run_invoices.py data --period 2026-09 --out "$T/out-fix" >/dev/null 2>&1)
a=$(invoice "$T/out-fix/invoices.jsonl" INV-2026-09-1047); [ "$a" = 4384.03 ]; step "3a fixed run gives the expected INV-1047 API line ($a)" $?
python3 "$HERE/oracle.py" "$T/fixed" > "$T/o2" 2>&1; step "3b oracle passes on the fix: $(cat "$T/o2")" $?

cp -r "$HERE/work" "$T/rec"
(cd "$T/rec" && find . -type f | sort | xargs md5sum) > "$T/before"
"$HERE/record.sh" "$T/rec" > "$T/rec.log" 2>&1; rc=$?
(cd "$T/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) > "$T/after"
[ $rc = 0 ] && [ -s "$T/rec/report.pmdb" ] && cmp -s "$T/before" "$T/after"; step "4a record.sh writes report.pmdb ($(du -h "$T/rec/report.pmdb" | cut -f1)) and nothing else" $?
"$PMDB" "$T/rec/report.pmdb" < "$HERE/query.pmdb" > "$T/q.out" 2>&1
ok=0; while IFS= read -r line; do [ -z "$line" ] && continue; grep -qF -- "$line" "$T/q.out" || { echo "  missing: $line"; ok=1; }; done < "$HERE/query_expect.txt"
step "4b query.pmdb surfaces the cause" $ok
exit $fail
