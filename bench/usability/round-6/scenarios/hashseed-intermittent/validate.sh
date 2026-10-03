#!/usr/bin/env bash
# Validate the hashseed-intermittent scenario. Usage: validate.sh [--rate N]
# (--rate N also measures the failure rate of the unfixed build over seeds 0..N-1).
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PMDB=${PMDB:-/home/ambrus/pytrace-recorder/bench/usability/round-5/_work/opt-pmdb/bin/pmdb}
TMP=$(mktemp -d /tmp/validate-hashseed-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
export PYTHONDONTWRITEBYTECODE=1
ok=0
step() { if [ "$1" = 0 ]; then echo "PASS: $2"; else echo "FAIL: $2"; ok=1; fi; }
toc_links() {  # prints the hrefs of the TOC of one page
  sed -n '/On this page/,/<\/nav>/p' "$1/guides/replication/index.html" | grep -o 'href="[^"]*"' | tr '\n' ' '
}

cp -r "$HERE/work" "$TMP/orig"
cp -r "$HERE/work" "$TMP/fixed"
patch -s -p1 -d "$TMP/fixed" < "$HERE/fix.patch"

# 1. The failing run (seed 316) shows the symptom; a typical run (seed 0) doesn't.
(cd "$TMP/orig" && PYTHONHASHSEED=316 python3 build.py site --out "$TMP/out316" 2>/dev/null)
(cd "$TMP/orig" && PYTHONHASHSEED=0 python3 build.py site --out "$TMP/out0" 2>/dev/null)
links316=$(toc_links "$TMP/out316"); links0=$(toc_links "$TMP/out0")
echo "  seed 316: $links316"; echo "  seed 0:   $links0"
broken=$(grep -l '<li class="toc-[0-9]"><a href="#">' -r "$TMP/out316" | wc -l)
[ "$broken" -gt 50 ] && ! grep -rq '<li class="toc-[0-9]"><a href="#">' "$TMP/out0"
step $? "failing run (seed 316) has broken TOC links on $broken pages; seed 0 has none"

# 2. The oracle fails the unfixed program.
python3 "$HERE/oracle.py" "$TMP/orig" > "$TMP/oracle-orig.txt"; s=$?
head -1 "$TMP/oracle-orig.txt" | sed 's/^/  /'
[ $s -ne 0 ]; step $? "oracle fails the unfixed program"

# 3. The fixed program builds the failing run correctly and passes the oracle.
(cd "$TMP/fixed" && PYTHONHASHSEED=316 python3 build.py site --out "$TMP/fixed316" 2>/dev/null)
! grep -rq '<li class="toc-[0-9]"><a href="#">' "$TMP/fixed316" && diff -rq "$TMP/fixed316" "$TMP/out0" > /dev/null
step $? "fixed program, seed 316: TOC links work and output equals the good build"
python3 "$HERE/oracle.py" "$TMP/fixed" | sed 's/^/  /'; s=${PIPESTATUS[0]}
step $s "oracle passes the fixed program"

# 4. record.sh writes report.pmdb, changes nothing else, and the query surfaces the cause.
cp -r "$HERE/work" "$TMP/rec"
(cd "$TMP/rec" && find . -type f | sort | xargs sha256sum) > "$TMP/before.txt"
start=$(date +%s)
"$HERE/record.sh" "$TMP/rec" > "$TMP/record.log" 2>&1; s=$?
echo "  record.sh: $(( $(date +%s) - start )) s, $(du -h "$TMP/rec/report.pmdb" 2>/dev/null | cut -f1) trace"
(cd "$TMP/rec" && find . -type f ! -name report.pmdb | sort | xargs sha256sum) > "$TMP/after.txt"
[ $s -eq 0 ] && [ -s "$TMP/rec/report.pmdb" ] && diff -q "$TMP/before.txt" "$TMP/after.txt" > /dev/null
step $? "record.sh writes report.pmdb and leaves no other changes"
"$PMDB" "$TMP/rec/report.pmdb" < "$HERE/query.pmdb" > "$TMP/query.out" 2>&1
missing=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  if ! grep -qF -- "$line" "$TMP/query.out"; then echo "  missing in query output: $line"; missing=1; fi
done < "$HERE/query_expect.txt"
step $missing "query.pmdb output contains every line of query_expect.txt"

if [ "${1:-}" = "--rate" ]; then
  n=${2:-500}; fails=0
  for s in $(seq 0 $((n - 1))); do
    r=$(cd "$TMP/orig" && PYTHONHASHSEED=$s python3 -c "
from quill.config import load_site_config
from quill.plugins import discover, order_plugins
site = load_site_config('site'); o = order_plugins(discover(site), site['plugins'])
print(int(o.index('toc') < o.index('heading-ids')))")
    fails=$((fails + r))
  done
  echo "  unfixed build broken for $fails of $n seeds"
fi
exit $ok
