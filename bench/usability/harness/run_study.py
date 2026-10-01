"""Runs the usability study.

Usage:
  python3 run_study.py plan                 # writes the run plan (fixed order) once
  python3 run_study.py run [--parallel 2] [--pilot] [--limit N] [--dry]
  python3 run_study.py status

Each run is executed in its own sandbox under `_work/runs/<run id>/`. A run interrupted by a usage
limit or an infrastructure error is discarded so that it is executed again by the next `run`.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import exercises
import prompts
import sandbox

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
RUNS = WORK / "runs"
PLAN = WORK / "plan.json"
RESULTS = WORK / "results.jsonl"
OPT = WORK / "opt-pmdb"
TOKEN_FILE = Path.home() / ".config" / "pmdb-study" / "oauth-token"

MODELS = ["sonnet", "haiku"]
ARMS = ["A", "B"]
TOOLS = "Bash,Read,Edit,Write,Grep,Glob"
MAX_TURNS = 60
TIMEOUT = 20 * 60
PLAN_SEED = 4242
PILOT_SEED = 7

LIMIT_PATTERNS = re.compile(
  r"usage limit|rate limit|limit reached|overloaded|529|Credit balance|"
  r"authentication|OAuth|401|invalid api key|ECONNRESET|ETIMEDOUT|socket hang up", re.I)

lock = threading.Lock()


def token():
  return TOKEN_FILE.read_text().strip()


def plan(args):
  if PLAN.exists():
    sys.exit(f"{PLAN} exists; delete it to make a new plan")
  ex = exercises.load(WORK / "exercises.json")
  runs = [{"exercise": e, "arm": a, "model": m} for e in ex for a in ARMS for m in MODELS]
  random.Random(PLAN_SEED).shuffle(runs)

  # The pilot exercise is another silent mutant, drawn with its own seed.
  mutants = json.load(open(WORK / "mutants.json"))
  chosen = {(e["program"], e["site"], e["operator"]) for e in ex.values()}
  silent = [m for m in mutants if m["fail_rate"] > 0 and not m["report_crashes"]
            and (m["program"], m["site"], m["operator"]) not in chosen
            and 0 < m["fail_rate"] <= 0.9]
  pilot = dict(random.Random(PILOT_SEED).choice(silent), category="pilot")
  pilot["id"] = f"pilot-{pilot['program']}"
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


def parse_stream(path):
  """Extracts metrics from a stream-json transcript."""
  metrics = {"tool_calls": 0, "tool_errors": 0, "pmdb_calls": 0, "pmdb_record_calls": 0,
             "pmdb_failed": 0, "bash_commands": [], "session_id": None, "model": None,
             "result": None}
  pending = {}
  for line in path.read_text().splitlines():
    try:
      event = json.loads(line)
    except json.JSONDecodeError:
      continue
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
      metrics["session_id"] = event.get("session_id")
      metrics["model"] = event.get("model")
    elif kind == "assistant":
      for block in event.get("message", {}).get("content", []):
        if block.get("type") == "tool_use":
          metrics["tool_calls"] += 1
          command = block.get("input", {}).get("command", "")
          if block.get("name") == "Bash":
            metrics["bash_commands"].append(command)
          uses_pmdb = bool(re.search(r"(^|[\s/;&|(])pmdb(\s|$)", command))
          uses_record = "pmdb-record" in command
          metrics["pmdb_calls"] += uses_pmdb
          metrics["pmdb_record_calls"] += uses_record
          pending[block.get("id")] = uses_pmdb or uses_record
    elif kind == "user":
      content = event.get("message", {}).get("content", [])
      for block in content if isinstance(content, list) else []:
        if block.get("type") == "tool_result":
          failed = bool(block.get("is_error"))
          text = json.dumps(block.get("content"))
          metrics["tool_errors"] += failed
          if pending.get(block.get("tool_use_id")) and (failed or "error:" in text):
            metrics["pmdb_failed"] += 1
    elif kind == "result":
      metrics["result"] = {k: event.get(k) for k in (
        "subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd",
        "usage", "result")}
  return metrics


def claimed(text):
  match = re.findall(r"RESULT:\s*(\{.*\})", text or "")
  if not match:
    return None
  try:
    return json.loads(match[-1])
  except json.JSONDecodeError:
    return None


def scrub(path, secret):
  if path.exists() and secret:
    path.write_text(path.read_text().replace(secret, "<token>"))


def execute(run, exercise, dry=False):
  """Executes one run and returns its result record, or `None` if it must be retried."""
  directory = RUNS / run["id"]
  if directory.exists():
    shutil.rmtree(directory)
  for d in ("home", "work"):
    (directory / d).mkdir(parents=True)
  sandbox.prepare_etc(directory)
  input_name = exercises.materialize(exercise, directory / "work")
  opt = OPT if run["arm"] == "B" else None
  secret = "" if dry else token()

  if run["arm"] == "B":
    r = subprocess.run(sandbox.command(directory, [
      "pmdb-record", "-o", "/work/report.pmdb", "main.py", input_name], opt=opt),
      capture_output=True, text=True, timeout=300)
    if not (directory / "work" / "report.pmdb").exists():
      raise RuntimeError(f"recording failed: {r.stderr[-500:]}")

  prompt = prompts.task(run["arm"], input_name)
  (directory / "prompt.txt").write_text(prompt)
  if dry:
    return None

  env = {"CLAUDE_CODE_OAUTH_TOKEN": secret}
  common = ["--model", run["model"], "--tools", TOOLS, "--allowedTools", TOOLS,
            "--permission-mode", "dontAsk", "--strict-mcp-config", "--setting-sources", ""]
  transcript = directory / "transcript.jsonl"
  started = time.time()
  with open(transcript, "w") as out:
    try:
      subprocess.run(sandbox.command(directory, [
        "claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
        "--max-turns", str(MAX_TURNS)] + common, opt=opt, env=env),
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
  shutil.copytree(directory / "work", final, ignore=shutil.ignore_patterns(
    "__pycache__", "*.pmdb", "*.trace"))
  grade = exercises.grade(exercise, final)
  exercises.write_sources(exercise, directory / "mutant")
  diff = subprocess.run(["diff", "-u", "-r", "-N", str(directory / "mutant"), str(final),
                         "-x", "__pycache__", "-x", "*.json", "-x", "*.txt"],
                        capture_output=True, text=True).stdout
  (directory / "fix.diff").write_text(diff)

  feedback = None
  if metrics["session_id"] and not timed_out:
    fb = subprocess.run(sandbox.command(directory, [
      "claude", "-p", prompts.FEEDBACK, "--resume", metrics["session_id"],
      "--output-format", "json", "--max-turns", "1"] + common, opt=opt, env=env),
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
    "program": exercise["program"], "mutated_function": exercise["function"],
    "model": metrics["model"], "timed_out": timed_out, "wall_seconds": round(wall, 1),
    "subtype": result.get("subtype"), "is_error": result.get("is_error"),
    "num_turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
    "usage": result.get("usage"), "notional_cost_usd": result.get("total_cost_usd"),
    "tool_calls": metrics["tool_calls"], "tool_errors": metrics["tool_errors"],
    "pmdb_calls": metrics["pmdb_calls"], "pmdb_record_calls": metrics["pmdb_record_calls"],
    "pmdb_failed": metrics["pmdb_failed"],
    "grade": grade, "diff_lines": sum(l[:1] in "+-" and l[:3] not in ("+++", "---")
                                      for l in diff.splitlines()),
    "success": grade["reported_ok"] and grade["generated_failures"] == 0,
    "claim": claim,
    "localized": bool(claim) and str(claim.get("function", "")).split(".")[-1].split("(")[0]
                 == exercise["function"].split(".")[-1],
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
      if not args.dry:
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
