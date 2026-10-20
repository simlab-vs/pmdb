#!/usr/bin/env bash
# Runs every scenario's validate.sh and summarizes the results.
# PMDB defaults to the build with `export`; each validate.sh reads it from the environment.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
export PMDB=${PMDB:-/home/ambrus/.claude/jobs/cb3d2dce/tmp/build/debug/pmdb}
status=0
for d in "$here"/scenarios/*/; do
  name="$(basename "$d")"
  start=$(date +%s)
  if bash "$d/validate.sh" > "/tmp/r7-validate-$name.log" 2>&1; then
    r=PASS
  else
    r=FAIL; status=1
  fi
  echo "$r $name ($(( $(date +%s) - start )) s, log /tmp/r7-validate-$name.log)"
done
exit $status
