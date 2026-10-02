"""Runs round 4 of the usability study.

Usage:
  python3 run_study.py plan                 # writes the run plan (fixed order) once
  python3 run_study.py run [--parallel 2] [--pilot] [--limit N] [--dry]
  python3 run_study.py status

Each run is executed in its own sandbox under `_work/runs/<run id>/`. A run interrupted by a usage
limit or an infrastructure error is discarded so that it is executed again by the next `run`.
With `--dry`, a run is prepared (materialized and, in arm B, recorded) but Claude isn't started.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs
import prompts
from pmdbbench.credentials import TOKEN_FILE, token  # noqa: F401
from pmdbbench.transcripts import claimed, parse_stream, scrub

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
RUNS = WORK / "runs"
PLAN = WORK / "plan.json"
EXERCISES = WORK / "exercises.json"
RESULTS = WORK / "results.jsonl"
OPT = WORK / "opt-pmdb"
SKILL = WORK / "skill"

MODELS = ["haiku", "sonnet", "opus"]
ARMS = ["A", "B"]
TOOLS = "Bash,Read,Edit,Write,Grep,Glob"
# The pmdb arm can also use skills, but only the pmdb skill: Claude Code always lists its bundled
# skills too, which can't be hidden, so their use is denied (as listed by `skill_check.py` for the
# version of Claude Code used).
TOOLS_B, ALLOWED_B = TOOLS + ",Skill", TOOLS + ",Skill(pmdb)"
BUNDLED_SKILLS = [
  "batch", "claude-api", "code-review", "dataviz", "debug", "deep-research", "doctor",
  "fewer-permission-prompts", "loop", "run", "run-skill-generator", "schedule", "simplify",
  "update-config", "verify", "workflow-authoring"]
DENIED_B = ",".join(f"Skill({s})" for s in BUNDLED_SKILLS)
# The skill as installed in the sandbox, and the variables it is used with (`bugs.command` sets
# them whenever /opt/pmdb is mounted).
SKILL_IN_SANDBOX = "/home/agent/.claude/skills/pmdb"
ENV_B = {"PYTHONPATH": "/opt/pmdb/python"}
MAX_TURNS = 60
TIMEOUT = 20 * 60
RECORD_TIMEOUT = 600
PLAN_SEED = 4242
PMDB = OPT / "bin" / "pmdb"

LIMIT_PATTERNS = re.compile(
  r"usage limit|rate limit|limit reached|overloaded|529|Credit balance|"
  r"authentication|OAuth|401|invalid api key|ECONNRESET|ETIMEDOUT|socket hang up", re.I)

# Run by `pmdb-record` from the directory the project's packages are imported from, so that the
# recorder instruments them; it runs the failing tests as the prompt says.
DRIVER = """\
import os
import sys

import pytest

os.chdir("/work")
sys.exit(pytest.main({args!r}))
"""
DRIVER_NAME = ".pmdb_driver.py"

lock = threading.Lock()


def plan(args):
  if PLAN.exists():
    sys.exit(f"{PLAN} exists; delete it to make a new plan")
  data = json.load(open(EXERCISES))
  ex = {e["id"]: e for e in data["exercises"]}
  runs = [{"exercise": e, "arm": a, "model": m} for e in ex for a in ARMS for m in MODELS]
  random.Random(PLAN_SEED).shuffle(runs)
  pilot = dict(data["pilot"], category="pilot")
  pilots = [{"exercise": pilot["id"], "arm": a, "model": "haiku", "pilot": True} for a in ARMS]
  for i, r in enumerate(pilots + runs):
    r["id"] = f"{i:02d}-{r['exercise']}-{r['arm']}-{r['model']}"
  json.dump({"exercises": {**ex, pilot["id"]: pilot}, "runs": pilots + runs},
            open(PLAN, "w"), indent=1)
  print(f"planned {len(runs)} runs and {len(pilots)} pilot runs")


def done_ids():
  if not RESULTS.exists():
    return set()
  return {json.loads(l)["id"] for l in RESULTS.read_text().splitlines() if l.strip()}


def paths(directory):
  result = set()
  for d, dirs, files in os.walk(directory):
    for name in dirs + files:
      result.add(os.path.relpath(os.path.join(d, name), directory))
  return result


def record_trace(directory, exercise):
  """Records the trace of the failing tests to /work/report.pmdb, leaving /work otherwise as it
  was. Returns a summary of the trace."""
  work = directory / "work"
  before = paths(work)
  relative = os.path.join(bugs.import_root(exercise), DRIVER_NAME)
  args = bugs.PYTEST_ARGS + bugs.cli_ids(exercise, exercise["failing_tests"])
  (work / relative).write_text(DRIVER.format(args=args))
  try:
    r = subprocess.run(bugs.command(directory, [
      "python", f"{SKILL_IN_SANDBOX}/scripts/pmdb-record", "-o", "/work/report.pmdb",
      os.path.join("/work", relative)], exercise, opt=OPT, env={"PYTHONDONTWRITEBYTECODE": "1"},
      network=True), capture_output=True, text=True, timeout=RECORD_TIMEOUT)
  finally:
    (work / relative).unlink()
  (directory / "recording.log").write_text(r.stdout + "\n--- stderr\n" + r.stderr)
  if not (work / "report.pmdb").exists():
    raise RuntimeError(f"recording failed: {r.stderr[-500:]}")
  # Remove whatever the tests wrote (beets writes a JUnit report to .reports/, for example).
  added = sorted(paths(work) - before - {"report.pmdb"})
  for p in sorted(added, key=len):
    p = work / p
    if p.is_dir() and not p.is_symlink():
      shutil.rmtree(p, ignore_errors=True)
    elif p.exists() or p.is_symlink():
      p.unlink()
  shown = subprocess.run([str(PMDB), "--show", "--brief", str(work / "report.pmdb")],
                         capture_output=True, text=True, timeout=300).stdout
  calls = re.findall(r"call ([\w.<>]+)\(", shown)
  names = {c.split(".")[-1] for c in calls}
  failed = re.findall(r"(\d+) failed", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
  summary = {"pytest_exit": r.returncode, "tests_failed": int(failed[0]) if failed else 0,
             "calls": len(calls), "functions": len(set(calls)),
             "fix_functions_recorded": [f for f in exercise["fix_functions"]
                                        if f.split(".")[-1] in names],
             "removed_after_recording": added, "size": (work / "report.pmdb").stat().st_size}
  # The trace is complete if the failing tests ran and failed under the recorder, as without it.
  summary["ok"] = (r.returncode == 1 and summary["tests_failed"] == len(exercise["failing_tests"])
                   and len(set(calls) - {"root"}) > 0)
  return summary


def execute(run, exercise, dry=False):
  """Executes one run and returns its result record, or `None` if it must be retried."""
  directory = RUNS / run["id"]
  if directory.exists():
    shutil.rmtree(directory)
  bugs.materialize(exercise, directory)
  opt = OPT if run["arm"] == "B" else None
  secret = "" if dry else token()

  trace = None
  if run["arm"] == "B":
    # The copy is writable, like a skill installed by a user, so that the run can be deleted.
    skill = directory / "home" / ".claude" / "skills" / "pmdb"
    shutil.copytree(SKILL, skill)
    for p in [skill, *skill.rglob("*")]:
      p.chmod(p.stat().st_mode | stat.S_IWUSR)
    trace = record_trace(directory, exercise)
    (directory / "trace.json").write_text(json.dumps(trace, indent=1))

  prompt = prompts.task(run["arm"], bugs.shell_ids(exercise, exercise["failing_tests"]))
  (directory / "prompt.txt").write_text(prompt)
  if dry:
    return None

  env = {"CLAUDE_CODE_OAUTH_TOKEN": secret}
  tools, allowed = (TOOLS_B, ALLOWED_B) if run["arm"] == "B" else (TOOLS, TOOLS)
  denied = ["--disallowedTools", DENIED_B] if run["arm"] == "B" else []
  # User settings come from the run's fresh home directory, which only holds the skill in arm B.
  common = ["--model", run["model"], "--tools", tools, "--allowedTools", allowed, *denied,
            "--permission-mode", "dontAsk", "--strict-mcp-config", "--setting-sources", "user"]
  transcript = directory / "transcript.jsonl"
  started = time.time()
  with open(transcript, "w") as out:
    try:
      subprocess.run(bugs.command(directory, [
        "claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
        "--max-turns", str(MAX_TURNS)] + common, exercise, opt=opt, env=env),
        stdout=out, stderr=subprocess.STDOUT, timeout=TIMEOUT)
      timed_out = False
    except subprocess.TimeoutExpired:
      timed_out = True
  wall = time.time() - started
  scrub(transcript, secret)
  metrics = parse_stream(transcript)

  result = metrics["result"] or {}
  text = result.get("result") or ""
  if not timed_out and (not metrics["result"] or (
      result.get("is_error") and LIMIT_PATTERNS.search(text + transcript.read_text()[-2000:]))):
    print(f"[{run['id']}] interrupted, will retry: {text[:200]!r}", flush=True)
    shutil.move(directory, directory.with_name(directory.name + f".interrupted-{int(started)}"))
    return None

  # Grade a copy of the final sources, before the feedback turn can touch them.
  final = directory / "final"
  shutil.copytree(directory / "work", final, symlinks=True, ignore=shutil.ignore_patterns(
    "__pycache__", ".pytest_cache", "*.pmdb", "*.trace"))
  grade = bugs.grade(exercise, final)
  bugs.write_work(exercise, directory / "original")
  diff = subprocess.run(["diff", "-u", "-r", "-N", str(directory / "original"), str(final),
                         "-x", "__pycache__", "-x", ".pytest_cache", "-x", "*.pmdb"],
                        capture_output=True, text=True, errors="replace").stdout
  (directory / "fix.diff").write_text(diff)

  feedback = None
  if metrics["session_id"] and not timed_out:
    fb = subprocess.run(bugs.command(directory, [
      "claude", "-p", prompts.FEEDBACK, "--resume", metrics["session_id"],
      "--output-format", "json", "--max-turns", "1"] + common, exercise, opt=opt, env=env),
      capture_output=True, text=True, timeout=600)
    (directory / "feedback.raw.json").write_text(fb.stdout.replace(secret, "<token>"))
    try:
      answer = json.loads(fb.stdout).get("result", "")
      feedback = json.loads(answer[answer.index("{"):answer.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
      feedback = {"unparsed": fb.stdout[-3000:]}

  claim = claimed(text)
  record = {
    "id": run["id"], "exercise": run["exercise"], "arm": run["arm"], "model_alias": run["model"],
    "pilot": run.get("pilot", False), "category": exercise["category"],
    "program": exercise["repo"], "bug": exercise["bug"],
    "mutated_function": exercise["fix_functions"][0], "fix_functions": exercise["fix_functions"],
    "model": metrics["model"], "timed_out": timed_out, "wall_seconds": round(wall, 1),
    "subtype": result.get("subtype"), "is_error": result.get("is_error"),
    "num_turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
    "usage": result.get("usage"), "notional_cost_usd": result.get("total_cost_usd"),
    "tool_calls": metrics["tool_calls"], "tool_errors": metrics["tool_errors"],
    "pmdb_calls": metrics["pmdb_calls"], "pmdb_record_calls": metrics["pmdb_record_calls"],
    "pmdb_failed": metrics["pmdb_failed"], "trace": trace,
    "grade": grade, "diff_lines": sum(l[:1] in "+-" and l[:3] not in ("+++", "---")
                                      for l in diff.splitlines()),
    "success": grade["reported_ok"] and grade["regressions"] == 0,
    "claim": claim,
    "localized": bugs.localized(claim, exercise["fix_functions"]),
    "feedback": feedback,
    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
  }
  return record


def run(args):
  data = json.load(open(PLAN))
  todo = [r for r in data["runs"] if r["id"] not in done_ids()
          and r.get("pilot", False) == args.pilot]
  if args.limit:
    todo = todo[:args.limit]
  print(f"{len(todo)} runs to execute", flush=True)
  stop = threading.Event()

  def work(r):
    if stop.is_set():
      return
    print(f"[{r['id']}] start", flush=True)
    try:
      record = execute(r, data["exercises"][r["exercise"]], dry=args.dry)
    except Exception as e:
      print(f"[{r['id']}] harness error: {e!r}", flush=True)
      return
    if record is None:
      if args.dry:
        trace = RUNS / r["id"] / "trace.json"
        print(f"[{r['id']}] prepared" + (f": trace {trace.read_text()}" if trace.exists() else ""),
              flush=True)
      else:
        stop.set()  # a usage limit was probably hit: stop starting new runs
      return
    with lock:
      with open(RESULTS, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[{r['id']}] done: success={record['success']} turns={record['num_turns']} "
          f"pmdb={record['pmdb_calls']}+{record['pmdb_record_calls']} "
          f"wall={record['wall_seconds']}s", flush=True)

  with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool:
    list(pool.map(work, todo))


def status(args):
  data = json.load(open(PLAN))
  done = done_ids()
  for pilot in (True, False):
    runs = [r for r in data["runs"] if r.get("pilot", False) == pilot]
    print(f"{'pilot' if pilot else 'main'}: {sum(r['id'] in done for r in runs)}/{len(runs)} done")


def main():
  parser = argparse.ArgumentParser()
  sub = parser.add_subparsers(dest="command", required=True)
  sub.add_parser("plan")
  r = sub.add_parser("run")
  r.add_argument("--parallel", type=int, default=2)
  r.add_argument("--pilot", action="store_true")
  r.add_argument("--limit", type=int, default=0)
  r.add_argument("--dry", action="store_true")
  sub.add_parser("status")
  args = parser.parse_args()
  {"plan": plan, "run": run, "status": status}[args.command](args)


if __name__ == "__main__":
  main()
