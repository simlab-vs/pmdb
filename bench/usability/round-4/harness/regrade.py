"""Grades again, with the network, the runs of exercises whose tests need it.

pipx's test session first downloads a package cache. Offline, every test of its test files fails,
so the offline grading of `run_study.py` failed every pipx run. `prepare.py`'s offline check (b)
had passed because its offline runs reused the cache downloaded by its online runs. The runs of
the exercises in `ONLINE` are graded again with the network; the offline grade is kept as
`grade_offline`.

Usage: python3 regrade.py   (rewrites ../_work/results.jsonl)
"""

import json
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
ONLINE = ("pipx-",)


def main():
  plan = json.loads((WORK / "plan.json").read_text())
  results = [json.loads(l) for l in (WORK / "results.jsonl").read_text().splitlines() if l.strip()]
  for r in results:
    exercise = plan["exercises"][r["exercise"]]
    if not exercise["bug"].startswith(ONLINE) or "grade_offline" in r:
      continue
    grade = bugs.grade(exercise, WORK / "runs" / r["id"] / "final", network=True)
    r["grade_offline"], r["grade"] = r["grade"], grade
    r["success"] = grade["reported_ok"] and grade["regressions"] == 0
    print(f"{r['id']}: success={r['success']} ({grade['passed']} passed, {grade['failed']} failed)",
          flush=True)
    (WORK / "results.jsonl").write_text("".join(json.dumps(x) + "\n" for x in results))


if __name__ == "__main__":
  main()
