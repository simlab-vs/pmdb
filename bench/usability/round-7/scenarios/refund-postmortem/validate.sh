#!/usr/bin/env bash
# Validate the refund-postmortem scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-5/_work/opt-pmdb/bin/pmdb}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
STATUS=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; STATUS=1; fi; }

# 1. The failing run (on the private export) reproduces the report in the issue.
cp -r "$HERE/work" "$TMP/pristine"
(cd "$TMP/pristine" && python3 monthly_report.py --export "$HERE/private/events-2026-09.jsonl.gz" \
  --month 2026-09 --out "$TMP/out1" 2>/dev/null)
grep -q "^novapay *350,695.74 *6,464.68 *16,966.45 *624.36 *326,640.25" "$TMP/out1/payout-recon-2026-09.txt"
step "1 failing run shows NovaPay refunds 16,966.45, net 326,640.25" $?
grep -q "^novapay" "$HERE/work/reports/payout-recon-2026-09.txt" && \
  diff <(grep -v Generated "$TMP/out1/payout-recon-2026-09.txt") <(grep -v Generated "$HERE/work/reports/payout-recon-2026-09.txt") >/dev/null
step "1 the report in work/ is the one the failing run writes" $?

# 2. The oracle fails on the pristine sources.
python3 "$HERE/oracle.py" "$TMP/pristine" >/dev/null
[ $? = 1 ]; step "2 oracle fails on pristine work" $?

# 3. The reference fix gives the statement's numbers and passes the oracle.
cp -r "$HERE/work" "$TMP/fixed"
patch -s -p1 -d "$TMP/fixed" < "$HERE/fix.patch"; step "3 fix.patch applies" $?
(cd "$TMP/fixed" && python3 monthly_report.py --export "$HERE/private/events-2026-09.jsonl.gz" \
  --month 2026-09 --out "$TMP/out3" 2>/dev/null)
grep -q "^novapay *350,695.74 *6,464.68 *11,938.78 *624.36 *331,667.92" "$TMP/out3/payout-recon-2026-09.txt" && \
  grep -q "^total .* 1,028,584.40" "$TMP/out3/payout-recon-2026-09.txt"
step "3 fixed run shows NovaPay refunds 11,938.78, net 331,667.92" $?
python3 "$HERE/oracle.py" "$TMP/fixed" >/dev/null; step "3 oracle passes on fixed work" $?

# 4. record.sh writes the trace and nothing else; the query surfaces the cause.
cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs md5sum) > "$TMP/before"
"$HERE/record.sh" "$TMP/rec" 2>/dev/null; step "4 record.sh succeeds" $?
[ -s "$TMP/rec/report.pmdb" ]; step "4 report.pmdb written ($(du -h "$TMP/rec/report.pmdb" | cut -f1))" $?
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) | diff - "$TMP/before" >/dev/null
step "4 no other file added or changed in WORKDIR" $?
"$PMDB" "$TMP/rec/report.pmdb" < "$HERE/query.pmdb" > "$TMP/query.out" 2>&1
MISSING=0
while IFS= read -r line; do
  grep -qF -- "$line" "$TMP/query.out" || { echo "  missing: $line"; MISSING=1; }
done < "$HERE/query_expect.txt"
step "4 query.pmdb output contains query_expect.txt" $MISSING
exit $STATUS
