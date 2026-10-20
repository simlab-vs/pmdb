#!/bin/sh
# Regenerates hidden/ (datasets + expected outputs of the fixed program).
set -e
S=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
rm -rf "$S/hidden"; mkdir -p "$S/hidden"
gen() { name=$1; shift; python3 "$S/gen/make_data.py" "$@" --out "$S/hidden/$name" > /dev/null; }
gen h1 --seed 11 --accounts 1800 --needle gs_legacy_to_ml
gen h2 --seed 23 --accounts 2200 --needle tx_legacy_to_ml --needle gs_to_ml --plain-exchanges 7
gen h3 --seed 37 --accounts 1500 --needle mixed_closing
mkdir -p "$S/hidden/original" && cp -r "$S/work/data" "$S/hidden/original/data" && cp "$S/gen/truth_original.json" "$S/hidden/original/truth.json"
cp -r "$S/work" "$TMP/fixed" && rm -rf "$TMP/fixed/data"
patch -s -p1 -d "$TMP/fixed" < "$S/fix.patch"
for case in original h1 h2 h3; do
  python3 "$TMP/fixed/run_billing.py" --period 2026-09 --data "$S/hidden/$case/data" --out "$S/hidden/$case/expected" > /dev/null 2>&1
done
