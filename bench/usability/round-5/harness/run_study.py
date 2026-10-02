"""Runs round 5 of the usability study.

Usage:
  python3 run_study.py plan                 # writes the run plan (fixed order) once
  python3 run_study.py run [--parallel 8] [--pilot] [--limit N] [--dry]
  python3 run_study.py status

Each run is executed in its own sandbox under `_work/runs/<run id>/`, without network: Claude Code
reaches the API through the relay of `offline.py`, started for the run and stopped after it. A run
interrupted by a usage limit or an infrastructure error is discarded so that it is executed again
by the next `run`. With `--dry`, a run is prepared (materialized, the skill installed in arm B, the
prompt written) but Claude isn't started.
"""

import argparse
import concurrent.futures
import datetime
import json
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs
import offline
import prompts
from pmdbbench.credentials import token
from pmdbbench.transcripts import claimed, parse_stream, scrub

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
RUNS = WORK / "runs"
PLAN = WORK / "plan.json"
EXERCISES = WORK / "exercises.json"
RESULTS = WORK / "results.jsonl"
OPT = bugs.OPT
SKILL = bugs.SKILL

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
MAX_TURNS = 80
TIMEOUT = 30 * 60
PLAN_SEED = 4242  # round 4's

LIMIT_PATTERNS = re.compile(
  r"usage limit|rate limit|limit reached|overloaded|529|Credit balance|"
  r"authentication|OAuth|401|invalid api key|ECONNRESET|ETIMEDOUT|ECONNREFUSED|socket hang up|"
  r"Unable to connect", re.I)
# Left out of the copy that is graded and compared with the original: caches and traces.
IGNORED = ["__pycache__", ".pytest_cache", "*.pmdb", "*.trace"]

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


def changed_paths(original, final):
  """Returns the paths, relative to /work, that differ between `original` and `final` (added,
  removed or modified), ignoring caches and traces."""
  excludes = [x for p in IGNORED for x in ("-x", p)]
  out = subprocess.run(["diff", "-rqN", *excludes, str(original), str(final)],
                       capture_output=True, text=True, errors="replace").stdout
  paths = []
  for line in out.splitlines():
    m = re.match(r"Files (.+) and (.+) differ$", line)
    if m and m.group(2).startswith(str(final) + "/"):
      paths.append(m.group(2)[len(str(final)) + 1:])
    elif line.startswith("Only in "):  # e.g. a special file diff -N can't compare
      directory, _, name = line[len("Only in "):].partition(": ")
      for base in (original, final):
        if directory == str(base) or directory.startswith(str(base) + "/"):
          paths.append(str(Path(directory[len(str(base)) + 1:]) / name))
  return sorted(set(paths))


def claude(directory, argv, exercise, arm, env, **kwargs):
  """Runs Claude Code in the run's sandbox, with the API relay running for its duration."""
  return offline.run(directory, argv, opt=OPT if arm == "B" else None,
                     env=bugs.environment(exercise, arm == "B", env),
                     binds=[(directory / "env", bugs.ENV_IN_SANDBOX)], api=True, **kwargs)


def execute(run, exercise, dry=False):
  """Executes one run and returns its result record, or `None` if it must be retried."""
  directory = RUNS / run["id"]
  if directory.exists():
    shutil.rmtree(directory)
  bugs.materialize(exercise, directory)
  if run["arm"] == "B":
    bugs.install_skill(directory)
  prompt = prompts.task(run["arm"], exercise["issue"])
  (directory / "prompt.txt").write_text(prompt)
  if dry:
    return None

  secret = token()
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
      claude(directory, ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
                         "--max-turns", str(MAX_TURNS)] + common, exercise, run["arm"], env,
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
  shutil.copytree(directory / "work", final, symlinks=True,
                  ignore=shutil.ignore_patterns(*IGNORED))
  grade = bugs.grade(exercise, final)
  bugs.write_work(exercise, directory / "original")
  excludes = [x for p in IGNORED for x in ("-x", p)]
  diff = subprocess.run(["diff", "-u", "-r", "-N", *excludes, str(directory / "original"),
                         str(final)], capture_output=True, text=True, errors="replace").stdout
  (directory / "fix.diff").write_text(diff)
  changed = changed_paths(directory / "original", final)
  test_files_changed = [p for p in changed if bugs.is_test(p)]

  feedback = None
  if metrics["session_id"] and not timed_out:
    fb = claude(directory, ["claude", "-p", prompts.FEEDBACK, "--resume", metrics["session_id"],
                            "--output-format", "json", "--max-turns", "1"] + common,
                exercise, run["arm"], env, capture_output=True, text=True, timeout=600)
    (directory / "feedback.raw.json").write_text(fb.stdout.replace(secret, "<token>"))
    try:
      answer = json.loads(fb.stdout).get("result", "")
      feedback = json.loads(answer[answer.index("{"):answer.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
      feedback = {"unparsed": fb.stdout[-3000:]}

  claim = claimed(text)
  traces = sorted(str(p.relative_to(directory / "work")) for p in (directory / "work").rglob("*")
                  if p.suffix in (".pmdb", ".trace") and p.is_file())
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
    "pmdb_failed": metrics["pmdb_failed"], "ran_pmdb_record": metrics["pmdb_record_calls"] > 0,
    "traces_left": traces,
    "changed_files": changed, "source_files_changed": [p for p in changed if p not in
                                                      test_files_changed],
    "test_files_changed": test_files_changed, "wrote_tests": bool(test_files_changed),
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
        print(f"[{r['id']}] prepared", flush=True)
      else:
        stop.set()  # a usage limit was probably hit: stop starting new runs
      return
    with lock:
      with open(RESULTS, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[{r['id']}] done: success={record['success']} turns={record['num_turns']} "
          f"pmdb={record['pmdb_calls']}+{record['pmdb_record_calls']} "
          f"tests={record['wrote_tests']} wall={record['wall_seconds']}s", flush=True)

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
  r.add_argument("--parallel", type=int, default=8)
  r.add_argument("--pilot", action="store_true")
  r.add_argument("--limit", type=int, default=0)
  r.add_argument("--dry", action="store_true")
  sub.add_parser("status")
  args = parser.parse_args()
  {"plan": plan, "run": run, "status": status}[args.command](args)


if __name__ == "__main__":
  main()
