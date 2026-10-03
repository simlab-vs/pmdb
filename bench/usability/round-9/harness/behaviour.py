"""Measures how agents worked in each run, from the transcripts, for the comparison of models.

Per run: the tools used (reads, searches, test runs, other commands, `pmdb-record`, pmdb,
edits), the steps of the first test run, the first `pmdb-record` and the first edit, the number
of edits and of distinct files edited, the steps after the first test run in which the failing
tests passed (effort after the fix), whether the agent wrote tests, and the failed tool calls.

Usage: python3 behaviour.py > ../results/behaviour.md   (also writes ../_work/behaviour.jsonl)
"""

import collections
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"

PYTEST = re.compile(r"\bpytest\b")
PMDB = re.compile(r"(^|[\s/;&|(])pmdb(\s|$)")
PDB = re.compile(r"\bpdb\b|breakpoint\(")
TRACE = re.compile(r"\bimport recorder\b|\bfrom recorder import\b|recorder\.load\(")  # the Python API


def steps(path):
  """Yields `(tool_use, tool_result)` pairs of a transcript, in order."""
  uses, order = {}, []
  for line in path.read_text().splitlines():
    try:
      e = json.loads(line)
    except json.JSONDecodeError:
      continue
    content = e.get("message", {}).get("content", [])
    if not isinstance(content, list):
      continue
    for b in content:
      if b.get("type") == "tool_use":
        uses[b["id"]] = [b, None]
        order.append(b["id"])
      elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
        uses[b["tool_use_id"]][1] = b
  for i in order:
    yield uses[i]


def text_of(result):
  if result is None:
    return ""
  c = result.get("content")
  if isinstance(c, list):
    return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
  return str(c or "")


def classify(use):
  name = use["name"]
  if name in ("Edit", "Write"):
    return "edit"
  if name == "Read":
    return "read"
  if name in ("Grep", "Glob"):
    return "search"
  if name == "Skill":
    return "skill"
  if name == "Bash":
    c = use["input"].get("command", "")
    if "pmdb-record" in c:
      return "record"
    if PMDB.search(c):
      return "pmdb"
    if TRACE.search(c):
      return "trace"
    if PYTEST.search(c):
      return "test"
    if PDB.search(c):
      return "pdb"
    if re.search(r"\bpython3? (-c|<<|-)|python3? \S+\.py", c):
      return "python"
    if re.search(r"^\s*(cat|head|tail|sed -n|less|nl)\b", c):
      return "read"
    if re.search(r"^\s*(grep|rg|find|ls)\b", c):
      return "search"
    return "shell"
  return name.lower()


def measure(run_dir, record):
  kinds = collections.Counter()
  order = []
  first_edit = None
  edited = collections.Counter()
  failed_calls = 0
  solved_at = None
  n = 0
  for n, (use, result) in enumerate(steps(run_dir / "transcript.jsonl"), 1):
    k = classify(use)
    kinds[k] += 1
    order.append(k)
    if result is not None and result.get("is_error"):
      failed_calls += 1
    if k == "edit":
      first_edit = first_edit or n
      edited[use["input"].get("file_path", "")] += 1
    if k == "test" and solved_at is None and first_edit is not None:
      out = text_of(result)
      if re.search(r"\b\d+ passed\b", out) and not re.search(r"\b\d+ (failed|error)", out):
        solved_at = n
  return {
    "id": record["id"], "exercise": record["exercise"], "model": record["model_alias"],
    "arm": record["arm"], "success": record["success"], "localized": record["localized"],
    "steps": n, "kinds": dict(kinds), "first_edit": first_edit, "edits": sum(edited.values()),
    "files_edited": len(edited), "rework": sum(v - 1 for v in edited.values()),
    "solved_at": solved_at, "after_solved": (n - solved_at) if solved_at else None,
    "failed_calls": failed_calls, "pmdb_calls": record["pmdb_calls"],
    "pmdb_failed": record["pmdb_failed"], "wrote_tests": record.get("wrote_tests"),
    "first_test": next((i for i, k in enumerate(order, 1) if k == "test"), None),
    "first_record": next((i for i, k in enumerate(order, 1) if k == "record"), None),
  }


def median(xs):
  xs = [x for x in xs if x is not None]
  return statistics.median(xs) if xs else None


def main():
  records = [json.loads(l) for l in (WORK / "results.jsonl").read_text().splitlines() if l.strip()]
  rows = [measure(WORK / "runs" / r["id"], r) for r in records if not r.get("pilot")]
  with open(WORK / "behaviour.jsonl", "w") as f:
    for row in rows:
      f.write(json.dumps(row) + "\n")

  kinds = ["read", "search", "test", "python", "trace", "pdb", "record", "pmdb", "skill", "edit", "shell"]
  print("# How agents worked, by model and arm\n")
  print("Medians per run, from `harness/behaviour.py`. Steps are tool calls. \"After solved\" counts "
        "the steps after the first test run, following an edit, in which the tests passed.\n")
  print("| model | arm | runs | success | wrote tests | steps | " + " | ".join(kinds)
        + " | first test run | first record | first edit | edits | rework | after solved | failed calls |")
  print("|" + "---|" * (len(kinds) + 13))
  groups = collections.defaultdict(list)
  for r in rows:
    groups[(r["model"], r["arm"])].append(r)
  for (m, a), rs in sorted(groups.items()):
    cells = [str(median(r["kinds"].get(k, 0) for r in rs)) for k in kinds]
    print(f"| {m} | {a} | {len(rs)} | {sum(r['success'] for r in rs)}/{len(rs)} | "
          f"{sum(bool(r['wrote_tests']) for r in rs)} | "
          f"{median(r['steps'] for r in rs)} | " + " | ".join(cells)
          + f" | {median(r['first_test'] for r in rs)} | {median(r['first_record'] for r in rs)}"
          f" | {median(r['first_edit'] for r in rs)} | {median(r['edits'] for r in rs)} | "
          f"{median(r['rework'] for r in rs)} | {median(r['after_solved'] for r in rs)} | "
          f"{median(r['failed_calls'] for r in rs)} |")
  print("\n## Runs\n")
  print("| run | success | steps | first edit | edits | rework | after solved | failed calls | tools |")
  print("|---|---|---|---|---|---|---|---|---|")
  for r in sorted(rows, key=lambda r: (r["exercise"], r["model"], r["arm"])):
    tools = ", ".join(f"{k} {v}" for k, v in sorted(r["kinds"].items(), key=lambda kv: -kv[1]))
    print(f"| {r['exercise']} {r['model']} {r['arm']} | {'✓' if r['success'] else '✗'} | {r['steps']} | "
          f"{r['first_edit']} | {r['edits']} | {r['rework']} | {r['after_solved']} | "
          f"{r['failed_calls']} | {tools} |")


if __name__ == "__main__":
  main()
