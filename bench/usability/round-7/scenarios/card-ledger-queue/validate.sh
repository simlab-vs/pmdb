#!/usr/bin/env bash
# Validate the card-ledger-queue scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/.claude/jobs/cb3d2dce/tmp/build/debug/pmdb}
DUMP="$HERE/private/card-events-2026-09-28.jsonl.gz"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export PYTHONDONTWRITEBYTECODE=1
STATUS=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; STATUS=1; fi; }
run() { (cd "$1" && python3 run_ledger.py --business-date 2026-09-28 --spool "$DUMP" --out "$2" --log "$2.log" 2>/dev/null); }

# 1. The failing run (on the consumed queue) reproduces the issue's numbers, and work/ holds its log and summary.
cp -r "$HERE/work" "$TMP/pristine"
run "$TMP/pristine" "$TMP/out1"
grep -q "^clearing *3955 *306,793.51" "$TMP/out1/settlement-2026-09-28.txt" && \
  grep -q "^net movement *-219,382.54" "$TMP/out1/settlement-2026-09-28.txt"
step "1 failing run shows clearings 306,793.51, net movement -219,382.54" $?
diff "$TMP/out1/settlement-2026-09-28.txt" "$HERE/work/reports/settlement-2026-09-28.txt" >/dev/null
step "1 the summary in work/ is the one the failing run writes" $?
diff <(grep -v 'from dump' "$TMP/out1.log" | cut -c24- | sed "s#$TMP/out1#/srv/cardledger/reports#g") \
     <(cut -c24- "$HERE/work/logs/cardledger-2026-09-28.log") >/dev/null
step "1 the log in work/ is the failing run's log" $?

# 2. The oracle fails on the pristine sources.
python3 "$HERE/oracle.py" "$TMP/pristine" >/dev/null
[ $? = 1 ]; step "2 oracle fails on pristine work" $?

# 3. The reference fix gives the bank's numbers and passes the oracle; plausible wrong fixes fail it.
cp -r "$HERE/work" "$TMP/fixed"
patch -s -p1 -d "$TMP/fixed" < "$HERE/fix.patch"; step "3 fix.patch applies" $?
run "$TMP/fixed" "$TMP/out3"
grep -q "^clearing *4235 *307,601.81" "$TMP/out3/settlement-2026-09-28.txt" && \
  grep -q "^net movement *-220,190.84" "$TMP/out3/settlement-2026-09-28.txt"
step "3 fixed run shows clearings 307,601.81, net movement -220,190.84" $?
python3 "$HERE/oracle.py" "$TMP/fixed" >/dev/null; step "3 oracle passes on fixed work" $?
for wrong in "$HERE"/wrong-fix-*.patch; do
  name=$(basename "$wrong" .patch)
  cp -r "$HERE/work" "$TMP/$name"
  patch -s -p1 -d "$TMP/$name" < "$wrong"
  python3 "$HERE/oracle.py" "$TMP/$name" >/dev/null
  [ $? = 1 ]; step "3 oracle fails $name" $?
done

# 4. record.sh writes the trace and nothing else; the query surfaces the cause.
cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs md5sum) > "$TMP/before"
"$HERE/record.sh" "$TMP/rec" 2>/dev/null; step "4 record.sh succeeds" $?
[ -s "$TMP/rec/report.pmdb" ]; step "4 report.pmdb written ($(du -h "$TMP/rec/report.pmdb" | cut -f1))" $?
(cd "$TMP/rec" && find . ! -name report.pmdb | sort) > "$TMP/after-names"
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) | diff - "$TMP/before" >/dev/null && \
  ! grep -q __pycache__ "$TMP/after-names"
step "4 no other file added or changed in WORKDIR" $?
mkdir "$TMP/q"
(cd "$TMP/q" && "$PMDB" "$TMP/rec/report.pmdb" < "$HERE/query.pmdb" && python3 "$HERE/query.py") > "$TMP/query.out" 2>&1
MISSING=0
while IFS= read -r line; do
  grep -qF -- "$line" "$TMP/query.out" || { echo "  missing: $line"; MISSING=1; }
done < "$HERE/query_expect.txt"
step "4 query.pmdb + query.py output contains query_expect.txt" $MISSING
exit $STATUS
