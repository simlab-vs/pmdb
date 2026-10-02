"""Checks the mined bugs against round 4's pre-registered exclusion rules.

For each bug of `data/bugs.jsonl`, the agent's view is materialized in a temporary sandbox root
and checked mechanically:
  (a) `reproducible`: the failing tests, run alone as the prompt says, fail in 3 of 3 runs at the
      parent's sources and pass in 3 of 3 runs with the fix's sources;
  (b) `offline`: the same holds with the network unshared (else the bug "needs network");
  (c) `few_failures`: at most 10 failing tests;
  (d) `fast`: the bug's test files run, offline with the fix's sources, in less than 60 s;
  (e) `recordable`: the skill's `pmdb-record` records the failing tests at the parent's sources as
      `run_study.py` does for arm B, and they fail under the recorder as they do without it
      (else arm B's trace would be broken).
Every check is run for every bug, so that all reasons are recorded; `reason` is the first failed
check in the order (a), (b), (c), (d), (e). The tests of the test files that pass in both offline runs
of (d) are recorded as `fix_passed`: the tests a fix must not break.

The output of the failing tests at the parent's sources (first offline run) is recorded as
`failing_output`, for the screen.

Usage: python3 prepare.py [bug id ...]   (writes ../data/prepared.jsonl)
"""

import json
import shutil
import sys
from pathlib import Path

import bugs
import run_study

ROOT = Path(__file__).resolve().parent.parent
BUGS = ROOT / "data" / "bugs.jsonl"
OUT = ROOT / "data" / "prepared.jsonl"
RUNS = 3
MAX_FAILING = 10
MAX_SECONDS = 60


def failing_runs(root, bug, network):
  """Returns the outcomes of the failing tests in `RUNS` runs."""
  ids = bugs.cli_ids(bug, bug["failing_tests"])
  results = []
  for _ in range(RUNS):
    r = bugs.run_tests(root, bug, ids, network=network)
    results.append(r)
  return results


def summary(runs, bug):
  return [{t: r["outcomes"].get(t, "missing") for t in bug["failing_tests"]} for r in runs]


def all_are(summaries, outcome):
  return all(v == outcome for s in summaries for v in s.values())


def check_recording(bug, exercise):
  """Records the failing tests as in arm B and returns `run_study.record_trace`'s summary."""
  with bugs.temporary_root() as t:
    root = bugs.materialize(bug, Path(t) / "root")
    shutil.copytree(run_study.SKILL, root / "home" / ".claude" / "skills" / "pmdb")
    try:
      return run_study.record_trace(root, exercise)
    except Exception as e:
      return {"ok": False, "error": repr(e)[-500:]}
    finally:
      for p in [root / "home", *(root / "home").rglob("*")]:
        if not p.is_symlink():
          p.chmod(p.stat().st_mode | 0o200)


def prepare(bug):
  record = {"id": bug["id"], "repo": bug["repo"], "fix_functions": bugs.fix_functions(bug),
            "restored_files": bugs.restored_files(bug),
            "failing_cli_ids": bugs.cli_ids(bug, bug["failing_tests"]),
            "import_root": bugs.import_root(bug)}
  checks = {}
  with bugs.temporary_root() as t:
    root = bugs.materialize(bug, Path(t) / "root")
    recording = check_recording(bug, dict(bug, fix_functions=record["fix_functions"]))
    parent = {net: summary(failing_runs(root, bug, net), bug) for net in (True, False)}
    offline_output = bugs.run_tests(root, bug, record["failing_cli_ids"], network=False)["output"]
    bugs.apply_fix(bug, root / "work")
    fixed = {net: summary(failing_runs(root, bug, net), bug) for net in (True, False)}
    full = [bugs.run_tests(root, bug, bug["test_files"], network=False) for _ in range(2)]

  for net, name in ((True, "reproducible"), (False, "offline")):
    checks[name] = all_are(parent[net], "failed") and all_are(fixed[net], "passed")
  checks["few_failures"] = len(bug["failing_tests"]) <= MAX_FAILING
  seconds = max(r["seconds"] for r in full)
  checks["fast"] = seconds < MAX_SECONDS and all(r["returncode"] != "timeout" for r in full)
  checks["recordable"] = bool(recording.get("ok"))

  passed = [set(t for t, o in r["outcomes"].items() if o == "passed") for r in full]
  record["fix_passed"] = sorted(passed[0] & passed[1])
  record["fix_flaky"] = sorted(passed[0] ^ passed[1])
  record["test_files_seconds"] = seconds
  record["test_files_counts"] = [{k: r[k] for k in ("passed", "failed", "skipped", "returncode")}
                                 for r in full]
  record["failing_runs"] = {"parent_online": parent[True], "parent_offline": parent[False],
                            "fix_online": fixed[True], "fix_offline": fixed[False]}
  record["failing_output"] = offline_output.replace(str(bugs.ROOT), "<host>")
  record["checks"] = checks
  record["recording"] = recording
  reasons = {"reproducible": "not_reproducible", "offline": "needs_network",
             "few_failures": "too_many_failing_tests", "fast": "slow_tests",
             "recordable": "not_recordable"}
  failed = [n for n, ok in checks.items() if not ok]
  record["reasons"] = [reasons[n] for n in failed]
  record["status"] = "eligible" if not failed else "excluded"
  record["reason"] = record["reasons"][0] if failed else None
  return record


def main(only):
  records = []
  for bug in bugs.load(BUGS):
    if only and bug["id"] not in only:
      continue
    record = prepare(bug)
    records.append(record)
    print(f"{bug['id']}: {record['status']} {record['reasons']} "
          f"({record['test_files_seconds']} s, {len(bug['failing_tests'])} failing, "
          f"recording ok: {record['recording'].get('ok')}, "
          f"fix functions {record['fix_functions']})", flush=True)
  if only:
    return
  with open(OUT, "w") as f:
    for r in records:
      f.write(json.dumps(r) + "\n")
  eligible = sum(r["status"] == "eligible" for r in records)
  print(f"{eligible} of {len(records)} bugs eligible; wrote {OUT}")


if __name__ == "__main__":
  main(sys.argv[1:])
