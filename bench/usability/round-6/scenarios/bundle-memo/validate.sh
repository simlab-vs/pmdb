#!/bin/sh
# Validate the bundle-memo scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-5/_work/opt-pmdb/bin/pmdb}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
status=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; status=1; fi; }
totals() { python3 -c "
import csv,sys
r={x['id']:x['total'] for x in csv.DictReader(open(sys.argv[1]))}
print(r['Q-30260'], r['Q-30457'])" "$1"; }

cp -r "$HERE/work" "$T/bug"
(cd "$T/bug" && PYTHONDONTWRITEBYTECODE=1 python3 quote_run.py data --date 2026-09-30 --out "$T/out-bug" 2>/dev/null)
[ "$(totals "$T/out-bug/quotes.csv")" = "72.59 55.78" ]; step "1 failing run shows the reported totals (72.59, 55.78)" $?

python3 "$HERE/oracle.py" "$T/bug" > "$T/oracle-bug.txt"; [ $? = 1 ]; step "2 oracle fails on pristine work: $(cut -c1-80 "$T/oracle-bug.txt")" $?

cp -r "$HERE/work" "$T/fix" && patch -s -p1 -d "$T/fix" < "$HERE/fix.patch"
(cd "$T/fix" && PYTHONDONTWRITEBYTECODE=1 python3 quote_run.py data --date 2026-09-30 --out "$T/out-fix" 2>/dev/null)
[ "$(totals "$T/out-fix/quotes.csv")" = "72.11 54.57" ]; step "3a fixed run gives the shop totals (72.11, 54.57)" $?
python3 "$HERE/oracle.py" "$T/fix" > /dev/null; step "3b oracle passes after fix.patch" $?

cp -r "$HERE/work" "$T/rec"
"$HERE/record.sh" "$T/rec"; [ -s "$T/rec/report.pmdb" ]; step "4a record.sh writes report.pmdb ($(du -h "$T/rec/report.pmdb" | cut -f1))" $?
[ "$(diff -r "$HERE/work" "$T/rec")" = "Only in $T/rec: report.pmdb" ]; step "4b record.sh leaves no other changes" $?
"$PMDB" "$T/rec/report.pmdb" < "$HERE/query.pmdb" > "$T/query.out" 2>&1
missing=0
while IFS= read -r line; do grep -qF "$line" "$T/query.out" || { echo "  missing: $line"; missing=1; }; done < "$HERE/query_expect.txt"
step "4c query.pmdb surfaces the cause" $missing
exit $status
