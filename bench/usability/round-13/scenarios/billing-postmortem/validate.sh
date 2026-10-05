#!/bin/sh
# Validate the billing-postmortem scenario on temporary copies of work/.
S=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-12/_work/opt-cli/bin/pmdb}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export PYTHONDONTWRITEBYTECODE=1
status=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; status=1; fi; }

# 0. The agent's workspace holds no input data.
[ ! -e "$S/work/data" ]; step "0 work/ holds no extract" $?

# 1. The reported run shows the symptom.
cp -r "$S/work" "$TMP/pristine"
(cd "$TMP/pristine" && python3 run_billing.py --period 2026-09 --data "$S/private/extract-2026-09" --out "$TMP/out_bug" > "$TMP/bug.txt" 2>&1)
cmp -s "$TMP/out_bug/summary_2026-09.txt" "$S/work/reports/summary_2026-09.txt"; step "1b the summary in work/reports is the failing run's" $?
grep -q "metered consumption      1,941,062.2 kWh" "$TMP/bug.txt" && grep -q "bills issued                   3,070" "$TMP/bug.txt"
step "1 failing run shows 1,941,062.2 kWh metered (MDM: 1,941,139.9) with 3,070 bills" $?

# 2. The oracle fails the pristine program.
python3 "$S/oracle.py" "$TMP/pristine" > "$TMP/oracle_bug.txt" 2>&1
[ $? -ne 0 ]; step "2 oracle fails pristine work" $?

# 3. The fix gives the expected result and passes the oracle (strict too).
cp -r "$S/work" "$TMP/fixed" && patch -s -p1 -d "$TMP/fixed" < "$S/fix.patch"
(cd "$TMP/fixed" && python3 run_billing.py --period 2026-09 --data "$S/private/extract-2026-09" --out "$TMP/out_fix" > "$TMP/fix.txt" 2>&1)
grep -q "metered consumption      1,941,139.9 kWh" "$TMP/fix.txt"; step "3a fixed run shows 1,941,139.9 kWh" $?
python3 "$S/oracle.py" --strict "$TMP/fixed" > "$TMP/oracle_fix.txt" 2>&1; step "3b oracle passes fixed work (--strict)" $?

# 4. Recording leaves only report.pmdb, and the query surfaces the cause.
cp -r "$S/work" "$TMP/rec"
"$S/record.sh" "$TMP/rec"; rc=$?
[ $rc -eq 0 ] && [ -s "$TMP/rec/report.pmdb" ]; step "4a record.sh writes report.pmdb" $?
[ "$(diff -r "$S/work" "$TMP/rec")" = "Only in $TMP/rec: report.pmdb" ]; step "4b no other changes in WORKDIR" $?
"$PMDB" "$TMP/rec/report.pmdb" < "$S/query.pmdb" > "$TMP/query.txt" 2>&1
ok=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  grep -qF -- "$line" "$TMP/query.txt" || { echo "   missing: $line"; ok=1; }
done < "$S/query_expect.txt"
step "4c query output contains query_expect.txt" $ok
exit $status
