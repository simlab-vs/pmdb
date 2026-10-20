#!/usr/bin/env bash
# Validate the payroll-postmortem scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/.claude/jobs/cb3d2dce/tmp/build/debug/pmdb}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
STATUS=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; STATUS=1; fi; }
REG=payroll-register-2026-09.txt
strip_log() { sed -E 's/^[0-9-]+ [0-9:,]+ //; s#/[^ ]*/(payroll-register|credit-transfers|hr-2026)#/X/\1#g' "$1"; }

# 1. The failing run (on the private export) reproduces the register and log in work/ and the issue's numbers.
cp -r "$HERE/work" "$TMP/pristine"
(cd "$TMP/pristine" && PYTHONDONTWRITEBYTECODE=1 python3 run_payroll.py --hr-export "$HERE/private/hr-2026-09.json" \
  --period 2026-09 --out "$TMP/out1" --bank-out "$TMP/bank1" --log "$TMP/run1.log" 2>/dev/null)
grep -q "^total *619 *2,163,813.44 *637,033.10 *65,119.99 *94,747.50 *2,960,714.03 .* 2,015,999.07 " "$TMP/out1/$REG"
step "1 failing run shows base salaries 2,163,813.44, allowances 94,747.50, net 2,015,999.07" $?
diff <(grep -v Generated "$TMP/out1/$REG") <(grep -v Generated "$HERE/work/reports/$REG") >/dev/null
step "1 the register in work/ is the one the failing run writes" $?
diff <(strip_log "$TMP/run1.log") <(strip_log "$HERE/work/logs/payroll-2026-09.log") >/dev/null
step "1 the log in work/ is the failing run's log" $?

# 2. The oracle fails on the pristine sources.
python3 "$HERE/oracle.py" "$TMP/pristine" >/dev/null
[ $? = 1 ]; step "2 oracle fails on pristine work" $?

# 3. The reference fix gives HR's numbers and passes the oracle; an incomplete fix fails it.
cp -r "$HERE/work" "$TMP/fixed"
patch -s -p1 -d "$TMP/fixed" < "$HERE/fix.patch"; step "3 fix.patch applies" $?
(cd "$TMP/fixed" && PYTHONDONTWRITEBYTECODE=1 python3 run_payroll.py --hr-export "$HERE/private/hr-2026-09.json" \
  --period 2026-09 --out "$TMP/out3" --bank-out "$TMP/bank3" 2>/dev/null)
grep -q "^total *619 *2,146,909.01 *637,033.10 *65,119.99 *94,245.00 *2,943,307.10 *552,863.24 *384,599.28 *2,005,844.58 *540,324.95" "$TMP/out3/$REG"
step "3 fixed run shows HR's preview (base 2,146,909.01, net 2,005,844.58)" $?
python3 "$HERE/oracle.py" "$TMP/fixed" >/dev/null; step "3 oracle passes on fixed work" $?
cp -r "$HERE/work" "$TMP/wrong"
patch -s -p1 -d "$TMP/wrong" < "$HERE/wrong-fix.patch" && { python3 "$HERE/oracle.py" "$TMP/wrong" >/dev/null; [ $? = 1 ]; }
step "3 oracle fails the incomplete fix (wrong-fix.patch: base salary only)" $?

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
