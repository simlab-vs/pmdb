#!/usr/bin/env bash
# Runs every scenario's validate.sh and summarizes the results.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
status=0
for d in "$here"/scenarios/*/; do
  name="$(basename "$d")"
  start=$(date +%s)
  if bash "$d/validate.sh" > "/tmp/r6-validate-$name.log" 2>&1; then
    r=PASS
  else
    r=FAIL; status=1
  fi
  echo "$r $name ($(( $(date +%s) - start )) s, log /tmp/r6-validate-$name.log)"
done
exit $status
