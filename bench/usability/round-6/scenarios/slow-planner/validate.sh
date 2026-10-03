#!/usr/bin/env bash
# Validates the scenario on temporary copies; prints PASS/FAIL per step, exits 0 iff all pass.
# Takes about 5-8 minutes (two full planner runs in parallel, then a recorded one).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PMDB="${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-5/_work/opt-pmdb/bin/pmdb}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ok=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; ok=1; fi; }

cp -r "$HERE/work" "$TMP/pristine"
cp -r "$HERE/work" "$TMP/fixed"
patch -p1 -s -d "$TMP/fixed" < "$HERE/fix.patch"; step "fix.patch applies" $?

run() { (cd "$TMP/$1" && python3 plan_day.py data/orders_2026-09-28.json --fleet data/fleet.json \
          -o "$TMP/out-$1" > "$TMP/$1.stdout" 2> "$TMP/$1.stderr"); }
run pristine & run fixed & wait
grep -q "capacity: T-44 carries 1614 kg, capacity 1600 kg" "$TMP/pristine.stdout"
step "(1) failing run shows the symptom ($(tail -1 "$TMP/pristine.stderr" | sed 's/.*done in //'))" $?
grep -q "^problems: 0" "$TMP/fixed.stdout"
step "(3a) fixed run has no problems ($(tail -1 "$TMP/fixed.stderr" | sed 's/.*done in //'))" $?

python3 "$HERE/oracle.py" "$TMP/pristine" > "$TMP/o1" 2>&1; r=$?
[ $r -ne 0 ] && grep -q '^FAIL' "$TMP/o1"; step "(2) oracle fails on pristine work: $(tail -1 "$TMP/o1" | cut -c1-100)" $?
python3 "$HERE/oracle.py" "$TMP/fixed" > "$TMP/o2" 2>&1; step "(3b) oracle passes on fixed work: $(tail -1 "$TMP/o2" | cut -c1-100)" $?

cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs md5sum) > "$TMP/before.md5"
start=$(date +%s)
"$HERE/record.sh" "$TMP/rec" 2> "$TMP/rec.log"; step "(4a) record.sh ($(( $(date +%s) - start )) s, $(du -m "$TMP/rec/report.pmdb" 2>/dev/null | cut -f1) MB)" $?
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) | diff -q - "$TMP/before.md5" > /dev/null
step "(4b) record.sh leaves no other changes" $?
(cd "$TMP/rec" && "$PMDB" report.pmdb < "$HERE/query.pmdb" > "$TMP/q.out" 2>&1); step "(4c) query.pmdb runs" $?
missing=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  grep -qF -- "$line" "$TMP/q.out" || { echo "  missing: $line"; missing=1; }
done < "$HERE/query_expect.txt"
step "(4d) query output contains query_expect.txt" $missing
exit $ok
