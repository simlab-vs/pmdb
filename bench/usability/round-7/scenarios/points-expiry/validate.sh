#!/usr/bin/env bash
# Validate the points-expiry scenario on temporary copies. Exit 0 iff every step passes.
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/.claude/jobs/cb3d2dce/tmp/build/debug/pmdb}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
STATUS=0
step() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; STATUS=1; fi; }

# Run the job like production (/srv/loyalty/nightly, database /srv/loyalty/data/points.db) under the simulated
# clock of Sep 30, 23:50:02 CEST; print its report JSON's path. $1 = work tree to run, $2 = name.
run_month_end() {
  local root="$TMP/$2"
  mkdir -p "$root/srv/loyalty/data"
  cp -r "$1" "$root/srv/loyalty/nightly"
  rm -f "$root/srv/loyalty/nightly/logs/"* "$root/srv/loyalty/nightly/reports/"*
  cp "$HERE/private/points-2026-09-30T2350.db" "$root/srv/loyalty/data/points.db"
  (cd "$root/srv/loyalty/nightly" && TZ=Europe/Berlin SIM_START=2026-09-30T23:50:02+02:00 SIM_STEP=0.048 \
    SIM_ROOT="$root/srv/loyalty/nightly" PYTHONPATH="$HERE/sim" PYTHONDONTWRITEBYTECODE=1 \
    python3 nightly.py --db "$root/srv/loyalty/data/points.db" --log logs/nightly-2026-09-30.log 2>/dev/null)
  for f in "$root/srv/loyalty/nightly/logs/"* "$root/srv/loyalty/nightly/reports/"*; do
    sed -i "s|$root||g" "$f"
  done
  echo "$root/srv/loyalty/nightly"
}
field() { python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {}, {'r': r}))" "$@"; }

# 1. The failing run reproduces the issue's numbers and the log and reports in work/.
P=$(run_month_end "$HERE/work" pristine)
J="$P/reports/nightly-2026-09-30.json"
[ "$(field "$J" "r['expiry']['expired_points'], r['expiry']['members_with_expiry'], r['liability']['outstanding_points'], r['liability']['value_eur'], r['liability']['expiring_next_month']['points']")" = "(742058, 1136, 16071024, '65891.20', 342633)" ]
step "1 failing run expires 742,058 points (1,136 members), outstanding 16,071,024, EUR 65891.20" $?
diff -r "$P/logs" "$HERE/work/logs" >/dev/null && diff -r "$P/reports" "$HERE/work/reports" >/dev/null
step "1 the log and reports in work/ are the ones the failing run writes" $?
grep -q "^2026-10-01 00:06:13,425 INFO loyalty: done" "$P/logs/nightly-2026-09-30.log"
step "1 the run crossed midnight (done at 00:06:13)" $?

# 2. The oracle fails on the pristine sources.
cp -r "$HERE/work" "$TMP/work-pristine"
python3 "$HERE/oracle.py" "$TMP/work-pristine" >/dev/null
[ $? = 1 ]; step "2 oracle fails on pristine work" $?

# 3. The reference fix gives the audit's numbers and passes the oracle; the wrong fix fails it.
cp -r "$HERE/work" "$TMP/work-fixed"
patch -s -p1 -d "$TMP/work-fixed" < "$HERE/fix.patch"; step "3 fix.patch applies" $?
F=$(run_month_end "$TMP/work-fixed" fixed)
python3 - "$F/reports/nightly-2026-09-30.json" "$HERE/private/expected-2026-09-30.json" <<'PY'
import json, sys
got, want = (json.load(open(p)) for p in sys.argv[1:])
assert (got["expiry"]["expired_points"], got["liability"]["outstanding_points"], got["liability"]["value_eur"]) == (468705, 16344377, "67011.95")
for section in ("posting", "expiry", "liability"):
    for key, value in want[section].items():
        assert got[section][key] == value, (section, key, got[section][key], value)
PY
step "3 fixed run gives the audit's figures (expired 468,705, outstanding 16,344,377, EUR 67011.95)" $?
python3 "$HERE/oracle.py" "$TMP/work-fixed" >/dev/null; step "3 oracle passes on fixed work" $?
cp -r "$HERE/work" "$TMP/work-wrong"
patch -s -p1 -d "$TMP/work-wrong" < "$HERE/wrong-fix.patch" && python3 "$HERE/oracle.py" "$TMP/work-wrong" >/dev/null
[ $? = 1 ]; step "3 oracle fails the wrong fix (cutoff shifted by a month)" $?

# 4. record.sh writes the trace and nothing else; the query surfaces the cause.
cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs md5sum) > "$TMP/before"
"$HERE/record.sh" "$TMP/rec" 2>/dev/null; step "4 record.sh succeeds" $?
[ -s "$TMP/rec/report.pmdb" ]; step "4 report.pmdb written ($(du -h "$TMP/rec/report.pmdb" | cut -f1))" $?
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs md5sum) | diff - "$TMP/before" >/dev/null
step "4 no other file added or changed in WORKDIR" $?
mkdir "$TMP/query"
(cd "$TMP/query" && "$PMDB" "$TMP/rec/report.pmdb" < "$HERE/query.pmdb" && python3 "$HERE/query.py") > "$TMP/query.out" 2>&1
MISSING=0
while IFS= read -r line; do
  grep -qF -- "$line" "$TMP/query.out" || { echo "  missing: $line"; MISSING=1; }
done < "$HERE/query_expect.txt"
step "4 query.pmdb + query.py output contains query_expect.txt" $MISSING
exit $STATUS
