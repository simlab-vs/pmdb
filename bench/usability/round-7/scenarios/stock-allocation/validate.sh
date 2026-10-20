#!/usr/bin/env bash
# Validate the stock-allocation scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/.claude/jobs/cb3d2dce/tmp/build/debug/pmdb}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
STATUS=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; STATUS=1; fi; }
DAY=2026-09-29
SYMPTOMS() { python3 "$HERE/gen/symptoms.py" "$1" $DAY "$HERE/private/levels-2026-09-29T0200.json" \
  "$HERE/work/input/orders-$DAY.jsonl" "$HERE/work/catalog"; }

# 1. The failing run (inventory answered from the private snapshot) gives the issue's symptoms,
#    and the log and summary in work/ are the ones it writes.
cp -r "$HERE/work" "$TMP/pristine"
sh "$HERE/gen/production_run.sh" "$TMP/pristine" "$TMP/prod1"
diff <(cut -c24- "$TMP/prod1/logs/allocation-$DAY.log") <(cut -c24- "$HERE/work/logs/allocation-$DAY.log") >/dev/null && \
  diff -r "$TMP/prod1/reports" "$HERE/work/reports" >/dev/null
step "1 the log and summary in work/ are the ones the failing run writes" $?
(cd "$TMP/pristine" && PYTHONPATH="$HERE/gen/service" INVENTORY_SNAPSHOT="$HERE/private/levels-$DAY""T0200.json" \
  PYTHONDONTWRITEBYTECODE=1 python3 allocate_night.py --orders input/orders-$DAY.jsonl --date $DAY \
  --out "$TMP/out1" --reports "$TMP/rep1" 2>/dev/null)
SYMPTOMS "$TMP/out1" > "$TMP/sym1"
grep -q "^short LEJ: 127 units missing over 18 SKUs" "$TMP/sym1" && \
  grep -q "^short RTM: 82 units missing over 19 SKUs" "$TMP/sym1" && \
  grep -q "^over-shipped: 335 units on 79 lines of 77 orders by channel {'marketplace': 79}" "$TMP/sym1" && \
  grep -q ",M-882837,1,HM-1128,R-19-09,11" "$TMP/out1/pick-RTM-$DAY.csv"
step "1 failing run: Leipzig 127 units short (18 SKUs), Rotterdam 82 (19), 335 units over-shipped on 79 lines" $?

# 2. The oracle fails on the pristine sources.
python3 "$HERE/oracle.py" "$TMP/pristine" >/dev/null
[ $? = 1 ]; step "2 oracle fails on pristine work" $?

# 3. The reference fix: no short picks, no over-shipping; the oracle passes. A partial fix fails.
cp -r "$HERE/work" "$TMP/fixed"
patch -s -p1 -d "$TMP/fixed" < "$HERE/fix.patch"; step "3 fix.patch applies" $?
(cd "$TMP/fixed" && PYTHONPATH="$HERE/gen/service" INVENTORY_SNAPSHOT="$HERE/private/levels-$DAY""T0200.json" \
  PYTHONDONTWRITEBYTECODE=1 python3 allocate_night.py --orders input/orders-$DAY.jsonl --date $DAY \
  --out "$TMP/out3" --reports "$TMP/rep3" 2>/dev/null)
SYMPTOMS "$TMP/out3" > "$TMP/sym3"
! grep -q "^short" "$TMP/sym3" && grep -q "^over-shipped: 0 units" "$TMP/sym3"
step "3 fixed run: no short picks, nothing over-shipped" $?
python3 "$HERE/oracle.py" "$TMP/fixed" >/dev/null; step "3 oracle passes on fixed work" $?
cp -r "$HERE/work" "$TMP/wrong"
patch -s -p1 -d "$TMP/wrong" < "$HERE/wrong-fix.patch"
python3 "$HERE/oracle.py" "$TMP/wrong" >/dev/null
[ $? = 1 ]; step "3 oracle fails the partial fix (wrong-fix.patch: ledger ignores non-positive reservations)" $?

# 4. record.sh writes the trace and nothing else; the query surfaces the cause.
cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs md5sum) > "$TMP/before"
"$HERE/record.sh" "$TMP/rec" 2>/dev/null; step "4 record.sh succeeds" $?
[ -s "$TMP/rec/report.pmdb" ]; step "4 report.pmdb written ($(du -h "$TMP/rec/report.pmdb" | cut -f1))" $?
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) | diff - "$TMP/before" >/dev/null
step "4 no other file added or changed in WORKDIR" $?
mkdir "$TMP/q"
(cd "$TMP/q" && "$PMDB" "$TMP/rec/report.pmdb" < "$HERE/query.pmdb" && python3 "$HERE/query.py") > "$TMP/query.out" 2>&1
MISSING=0
while IFS= read -r line; do
  grep -qF -- "$line" "$TMP/query.out" || { echo "  missing: $line"; MISSING=1; }
done < "$HERE/query_expect.txt"
step "4 query.pmdb + query.py output contains query_expect.txt" $MISSING
exit $STATUS
