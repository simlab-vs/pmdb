"""Checks round 5's bugs against the pre-registered exclusion rules.

For each bug of `data/bugs.jsonl` (round 4's bugs whose fix closes an issue), every check runs
offline (the sandbox has no network) and in a fresh materialization of the grading view (the
parent's tree with the fix commit's test files), so that no check can reuse what an earlier run
downloaded or wrote:
  (a) `reproducible`: the failing tests, run alone, fail in 3 of 3 runs at the parent's sources and
      pass in 3 of 3 runs with the fix's sources;
  (b) `offline`: (a) holds without network; in round 5 every run is offline, so a bug failing (a)
      fails (b) too, and the reason recorded is "not_reproducible_offline";
  (c) `few_failures`: at most 10 failing tests;
  (d) `fast`: the bug's test files run with the fix's sources in less than 60 s;
  (e) `recordable`: the failing tests, recorded with the skill's `pmdb-record` (the current
      recorder) at the parent's sources, fail under the recorder as they do without it, and the
      trace records functions of the project;
  (f) `issue`: the issue text (`bugs.issue_text`) has at least 80 characters.
Before the checks, every bug of a repository in `EXCLUDED_REPOSITORIES` is excluded with the
reason "excluded_repository", and none of its checks is run. This is the user's decision for
pypa/pipx: its tests need the network (its test session downloads a package cache) and time out
offline.
Every check is run for every other bug, so that all reasons are recorded; `reason` is the first
failed check in the order above. Repeated runs of a check stop once the check has failed. The
tests of the test files that pass in both runs of (d) are recorded as `fix_passed`: the tests a
fix must not break.

Usage: python3 prepare.py [bug id ...]   (writes ../data/prepared.jsonl when run on all bugs)
"""

import json
import sys
from pathlib import Path

import bugs

ROOT = Path(__file__).resolve().parent.parent
BUGS = ROOT / "data" / "bugs.jsonl"
OUT = ROOT / "data" / "prepared.jsonl"
RUNS = 3
MAX_FAILING = 10
MAX_SECONDS = 60
MIN_ISSUE_CHARACTERS = 80
EXCLUDED_REPOSITORIES = {"pypa/pipx"}  # the user's decision: the tests need the network


def failing_runs(root, bug, expected):
  """Returns the outcomes of the failing tests in up to `RUNS` runs, and the first run's output.

  The runs stop at the first one in which a test's outcome isn't `expected`: the check has then
  failed (pipx's offline runs each take the 600 s timeout)."""
  ids = bugs.cli_ids(bug, bug["failing_tests"])
  summaries, output = [], None
  for _ in range(RUNS):
    r = bugs.run_tests(root, bug, ids)
    output = r["output"] if output is None else output
    summaries.append({t: r["outcomes"].get(t, "missing") for t in bug["failing_tests"]})
    if not all_are(summaries[-1:], expected):
      break
  return summaries, output


def all_are(summaries, outcome):
  return all(v == outcome for s in summaries for v in s.values())


def prepare(bug, issue):
  record = {"id": bug["id"], "repo": bug["repo"], "fix_functions": bugs.fix_functions(bug),
            "hidden_test_files": bugs.hidden_test_files(bug),
            "failing_cli_ids": bugs.cli_ids(bug, bug["failing_tests"]),
            "import_root": bugs.import_root(bug), "issue_characters": len(issue)}
  bug = dict(bug, fix_functions=record["fix_functions"])
  checks = {}
  with bugs.temporary_root() as t:  # (a) at the parent
    root = bugs.materialize(bug, Path(t) / "root", tests=True)
    parent, output = failing_runs(root, bug, "failed")
  with bugs.temporary_root() as t:  # (a) with the fix
    root = bugs.materialize(bug, Path(t) / "root", tests=True)
    bugs.apply_fix(bug, root / "work")
    fixed, _ = failing_runs(root, bug, "passed")
  with bugs.temporary_root() as t:  # (d)
    root = bugs.materialize(bug, Path(t) / "root", tests=True)
    bugs.apply_fix(bug, root / "work")
    full = [bugs.run_tests(root, bug, bug["test_files"])]
    if full[0]["returncode"] != "timeout":  # else the check has failed
      full.append(bugs.run_tests(root, bug, bug["test_files"]))
  with bugs.temporary_root() as t:  # (e)
    root = bugs.materialize(bug, Path(t) / "root", tests=True)
    bugs.install_skill(root)
    try:
      recording = bugs.record_failing_tests(root, bug)
    except Exception as e:
      recording = {"ok": False, "error": repr(e)[-500:]}

  checks["reproducible"] = (len(parent) == len(fixed) == RUNS and all_are(parent, "failed")
                            and all_are(fixed, "passed"))
  checks["offline"] = checks["reproducible"]
  checks["few_failures"] = len(bug["failing_tests"]) <= MAX_FAILING
  seconds = max(r["seconds"] for r in full)
  checks["fast"] = (len(full) == 2 and seconds < MAX_SECONDS
                    and all(r["returncode"] != "timeout" for r in full))
  checks["recordable"] = bool(recording.get("ok"))
  checks["issue"] = len(issue) >= MIN_ISSUE_CHARACTERS

  passed = [set(t for t, o in r["outcomes"].items() if o == "passed") for r in full]
  record["fix_passed"] = sorted(set.intersection(*passed))
  record["fix_flaky"] = sorted(set.union(*passed) - set.intersection(*passed))
  record["test_files_seconds"] = seconds
  record["test_files_counts"] = [{k: r[k] for k in ("passed", "failed", "skipped", "returncode")}
                                 for r in full]
  record["failing_runs"] = {"parent": parent, "fix": fixed}
  record["failing_output"] = output.replace(str(bugs.ROUND4), "<host>").replace(str(ROOT), "<host>")
  record["checks"] = checks
  record["recording"] = recording
  reasons = {"reproducible": "not_reproducible_offline", "offline": "not_reproducible_offline",
             "few_failures": "too_many_failing_tests", "fast": "slow_tests",
             "recordable": "not_recordable", "issue": "issue_too_short"}
  failed = [n for n, ok in checks.items() if not ok]
  record["reasons"] = sorted(set(reasons[n] for n in failed), key=list(reasons.values()).index)
  record["status"] = "eligible" if not failed else "excluded"
  record["reason"] = record["reasons"][0] if failed else None
  return record


def main(only):
  texts = bugs.issues()
  records = []
  for bug in bugs.load(BUGS):
    if only and bug["id"] not in only:
      continue
    if bug["repo"] in EXCLUDED_REPOSITORIES:
      record = {"id": bug["id"], "repo": bug["repo"], "status": "excluded",
                "reason": "excluded_repository", "reasons": ["excluded_repository"]}
      records.append(record)
      print(f"{bug['id']}: excluded ['excluded_repository']", flush=True)
      continue
    record = prepare(bug, texts.get(bug["id"], ""))
    records.append(record)
    print(f"{bug['id']}: {record['status']} {record['reasons']} "
          f"({record['test_files_seconds']} s, {len(bug['failing_tests'])} failing, "
          f"recording {record['recording'].get('ok')}, issue {record['issue_characters']} chars, "
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
