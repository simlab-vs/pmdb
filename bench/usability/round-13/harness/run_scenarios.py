"""Runs six post-mortem scenarios for round 13 (round 7's five and billing-postmortem) in four
conditions, each scenario × condition × model `REPETITIONS` times:
- A: no trace, no pmdb;
- Q: the trace and the pmdb command-line tool, with its query language's reference in the prompt;
- P: the trace and pmdb's Python library (`recorder`), with its reference in the prompt;
- F: the trace and its binary format's specification in the prompt, no tool.
The pmdb arms are told to use the trace. No arm gets a skill, and no run gets the feedback
questionnaire.

Usage:
  python3 run_scenarios.py plan
  python3 run_scenarios.py run [--parallel 8] [--only SCENARIO] [--exclude SCENARIO]... [--dry]
  python3 run_scenarios.py status

A run copies the scenario's `work/` to the sandbox's /work. In arm B, the pmdb skill is installed as
a user skill (bundled skills denied, as in round 5) and the reported run is recorded to
/work/report.pmdb with the scenario's `record.sh`, in the sandbox. Claude Code then runs without
network, reaching only the API through round 5's relay (`offline.py`). The scenario's `oracle.py`
grades a copy of the final /work, in the sandbox too, since it runs the agent's code.
"""

import argparse
import concurrent.futures
import datetime
import json
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
import offline
from pmdbbench import sandbox
from pmdbbench.credentials import token
from pmdbbench.transcripts import claimed, parse_stream, scrub

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIRS = [ROOT.parent / "round-7" / "scenarios", ROOT / "scenarios"]  # round 7's, unchanged
WORK = ROOT / "_work"
RUNS = WORK / "runs"
PLAN = WORK / "plan.json"
RESULTS = WORK / "results.jsonl"
OPT = WORK / "opt-pmdb"          # the recorder, for recording; also what arm P's agent gets
OPT_Q = WORK / "opt-cli"          # what arm Q's agent gets: bin/pmdb only
AGENT_OPT = {"A": None, "Q": OPT_Q, "P": OPT, "F": None}
AGENT_ENV = {"P": {"PYTHONPATH": "/opt/pmdb/python"}}
TRACE_ARMS = ("Q", "P", "F")
MODEL_ORDER = {"haiku": 0, "sonnet": 1, "opus": 2}  # longest runs first
SKILL = WORK / "skill"
SKILL_IN_SANDBOX = "/home/agent/.claude/skills/pmdb"

MODELS = ["haiku", "sonnet", "opus"]
ARMS = ["A", "Q", "P", "F"]
TOOLS = "Bash,Read,Edit,Write,Grep,Glob"
TOOLS_B, ALLOWED_B = TOOLS + ",Skill", TOOLS + ",Skill(pmdb)"
BUNDLED_SKILLS = [
  "batch", "claude-api", "code-review", "dataviz", "debug", "deep-research", "doctor",
  "fewer-permission-prompts", "loop", "run", "run-skill-generator", "schedule", "simplify",
  "update-config", "verify", "workflow-authoring"]
DENIED_B = ",".join(f"Skill({s})" for s in BUNDLED_SKILLS)
MAX_TURNS = 80
TIMEOUT = 24 * 60  # so that the round fits in about 30 minutes
PLAN_SEED = 13
SCENARIO_NAMES = ["billing-postmortem", "card-ledger-queue", "payroll-postmortem",
                  "points-expiry", "refund-postmortem", "stock-allocation"]
REPETITIONS = 1
ENV_B = {"PYTHONPATH": "/opt/pmdb/python"}
PATCH = shutil.which("patch")
LIMIT_PATTERNS = re.compile(
  r"usage limit|rate limit|limit reached|overloaded|Credit balance|authentication|OAuth|"
  r"invalid api key|ECONNRESET|ETIMEDOUT|ECONNREFUSED|socket hang up|Unable to connect", re.I)
IGNORED = ["__pycache__", ".pytest_cache", "*.pmdb"]

TASK = """\
A user reported the following problem with the Python program in /work:

{issue}

{tools} There is no network access. Find the root cause and fix it with a minimal change to the \
program's source code. When you are done, end your reply with a line of the form

RESULT: {{"file": "<file you fixed>", "function": "<function you fixed>", "cause": "<one sentence>"}}
"""
HERE = Path(__file__).resolve().parent
REFERENCE = {arm: (HERE / f"{name}_reference.txt").read_text().strip()
             for arm, name in [("Q", "query"), ("P", "python"), ("F", "format")]}
TOOLS_TEXT = {
  "A": "Python 3 is installed, including pdb.",
  "Q": "Python 3 is installed, including pdb. pmdb, a trace-query debugger, is also installed, "
       "and a trace of the run the user reported has been recorded. Use pmdb and this trace in "
       "your investigation.\n\n" + REFERENCE["Q"] + "\n\n",
  "P": "Python 3 is installed, including pdb. pmdb's Python library for querying traces is also "
       "installed, and a trace of the run the user reported has been recorded. Use the library "
       "and this trace in your investigation.\n\n" + REFERENCE["P"] + "\n\n",
  "F": "Python 3 is installed, including pdb. A trace of the run the user reported has been "
       "recorded; no tool to read it is installed, so write your own reader if you need one. "
       "Use this trace in your investigation.\n\n" + REFERENCE["F"] + "\n\n",
}
FEEDBACK = (ROOT.parent / "round-5" / "harness" / "prompts.py")  # round 5's questionnaire

lock = threading.Lock()


def feedback_prompt():
  namespace = {}
  exec(FEEDBACK.read_text(), namespace)
  return namespace["FEEDBACK"]


def scenarios():
  return [s for s in SCENARIO_NAMES if (scenario_dir(s) / "oracle.py").exists()]


def scenario_dir(name):
  return next(d / name for d in SCENARIO_DIRS if (d / name).is_dir())


def plan(args):
  if PLAN.exists():
    sys.exit(f"{PLAN} exists; delete it to make a new plan")
  runs = [{"scenario": s, "arm": a, "model": m, "repetition": k} for s in scenarios()
          for a in ARMS for m in MODELS for k in range(1, REPETITIONS + 1)]
  random.Random(PLAN_SEED).shuffle(runs)
  runs.sort(key=lambda r: MODEL_ORDER[r["model"]])  # stable: shuffled within each model
  for i, r in enumerate(runs):
    r["id"] = f"{i:02d}-{r['scenario']}-{r['arm']}-{r['model']}-{r['repetition']}"
  PLAN.write_text(json.dumps({"runs": runs}, indent=1))
  print(f"planned {len(runs)} runs")


def done_ids():
  if not RESULTS.exists():
    return set()
  return {json.loads(l)["id"] for l in RESULTS.read_text().splitlines() if l.strip()}


def writable(path):
  for p in [path, *path.rglob("*")]:
    if not p.is_symlink():
      p.chmod(p.stat().st_mode | stat.S_IWUSR)


def execute(run, dry=False):
  directory = RUNS / run["id"]
  if directory.exists():
    writable(directory)
    shutil.rmtree(directory)
  source = scenario_dir(run["scenario"])
  (directory / "home").mkdir(parents=True)
  shutil.copytree(source / "work", directory / "work", symlinks=True)
  offline.prepare_etc(directory)
  arm_b = False  # no arm gets the skill
  env = dict(AGENT_ENV.get(run["arm"], {}))

  if arm_b:
    skill = directory / "home" / ".claude" / "skills" / "pmdb"
    shutil.copytree(SKILL, skill)
    writable(skill)
  if run["arm"] in TRACE_ARMS:
    # Arm C gets the trace but neither pmdb nor the skill: the recorder and `pmdb-record` are
    # mounted for recording only.
    r = offline.run(directory, ["sh", "/scenario/record.sh", "/work"], opt=OPT,
                    env={"SKILL": "/recording-skill", "PMDB_PYTHONPATH": "/opt/pmdb/python"},
                    binds=[(source, "/scenario"), (SKILL, "/recording-skill")],  # never for the agent
                    capture_output=True, text=True, timeout=1800)
    (directory / "recording.log").write_text(r.stdout + "\n--- stderr\n" + r.stderr)
    if not (directory / "work" / "report.pmdb").exists():
      raise RuntimeError(f"recording failed: {r.stderr[-500:]}")
  shutil.copytree(directory / "work", directory / "original", symlinks=True,
                  ignore=shutil.ignore_patterns(*IGNORED))

  prompt = TASK.format(issue=(source / "issue.md").read_text().strip(), tools=TOOLS_TEXT[run["arm"]])
  (directory / "prompt.txt").write_text(prompt)
  if dry:
    return None

  secret = token()
  env["CLAUDE_CODE_OAUTH_TOKEN"] = secret
  tools, allowed = (TOOLS_B, ALLOWED_B) if arm_b else (TOOLS, TOOLS)
  denied = ["--disallowedTools", DENIED_B] if arm_b else []
  common = ["--model", run["model"], "--tools", tools, "--allowedTools", allowed, *denied,
            "--permission-mode", "dontAsk", "--strict-mcp-config", "--setting-sources", "user"]
  transcript = directory / "transcript.jsonl"
  started = time.time()
  with open(transcript, "w") as out:
    try:
      offline.run(directory, ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
                              "--max-turns", str(MAX_TURNS)] + common,
                  opt=AGENT_OPT[run["arm"]], env=env, api=True,
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
      result.get("is_error") and result.get("subtype") != "error_max_turns"
      and LIMIT_PATTERNS.search(text))):
    print(f"[{run['id']}] interrupted, will retry: {text[:200]!r}", flush=True)
    shutil.move(directory, directory.with_name(directory.name + f".interrupted-{int(started)}"))
    return None

  usage = total_usage(transcript)
  final = directory / "final"
  shutil.copytree(directory / "work", final, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED))
  g = grade(directory, source, final)
  diff = subprocess.run(["diff", "-ruN", *[x for p in IGNORED for x in ("-x", p)],
                         str(directory / "original"), str(final)],
                        capture_output=True, text=True, errors="replace").stdout
  (directory / "fix.diff").write_text(diff)

  feedback = None
  if False:  # no feedback questionnaire in this round
    fb = offline.run(directory, ["claude", "-p", feedback_prompt(), "--resume",
                                 metrics["session_id"], "--output-format", "json",
                                 "--max-turns", "1"] + common,
                     opt=AGENT_OPT[run["arm"]], env=env, api=True,
                     capture_output=True, text=True, timeout=600)
    (directory / "feedback.raw.json").write_text(fb.stdout.replace(secret, "<token>"))
    try:
      answer = json.loads(fb.stdout).get("result", "")
      feedback = json.loads(answer[answer.index("{"):answer.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
      feedback = {"unparsed": fb.stdout[-3000:]}

  return {
    "id": run["id"], "scenario": run["scenario"], "exercise": run["scenario"], "arm": run["arm"],
    "repetition": run["repetition"],
    "model_alias": run["model"], "model": metrics["model"], "pilot": False,
    "category": "designed", "timed_out": timed_out, "wall_seconds": round(wall, 1),
    "subtype": result.get("subtype"), "is_error": result.get("is_error"),
    "num_turns": usage["num_turns"], "usage": usage["usage"], "usage_source": usage["source"],
    "tool_calls": metrics["tool_calls"], "tool_errors": metrics["tool_errors"],
    "pmdb_calls": metrics["pmdb_calls"], "pmdb_record_calls": metrics["pmdb_record_calls"],
    "pmdb_failed": metrics["pmdb_failed"],
    "success": g.returncode == 0, "oracle_tail": (g.stdout + g.stderr)[-1500:],
    "diff_lines": sum(l[:1] in "+-" and l[:3] not in ("+++", "---") for l in diff.splitlines()),
    "claim": claimed(text), "localized": None, "feedback": feedback,
    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
  }


USAGE_KEYS = ["input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
              "output_tokens"]


def total_usage(transcript):
  """The tokens and turns of a session: summed over all its result events (a session ends once more
  when a background task it started finishes), or, if it has none (it timed out), over the API
  responses of its assistant messages, counting each message once."""
  results, messages = [], {}
  for line in transcript.read_text(errors="replace").splitlines():
    try:
      e = json.loads(line)
    except json.JSONDecodeError:
      continue
    if e.get("type") == "result" and e.get("usage"):
      results.append(e)
    elif e.get("type") == "assistant":
      m = e.get("message", {})
      if m.get("id") and m.get("usage"):
        messages[m["id"]] = m["usage"]
  if results:
    return {"source": "result", "num_turns": sum(e.get("num_turns") or 0 for e in results),
            "usage": {k: sum(e["usage"].get(k, 0) for e in results) for k in USAGE_KEYS}}
  return {"source": "messages", "num_turns": len(messages),
          "usage": {k: sum(u.get(k, 0) for u in messages.values()) for k in USAGE_KEYS}}


def grade(directory, source, final):
  """Runs the scenario's oracle on `final` in the run's sandbox, with `patch` (which some oracles
  use to build their reference) on the PATH, and writes its output to `oracle.log`."""
  path = ":".join([str(Path(PATCH).parent)] + sandbox.TOOL_DIRS)
  g = offline.run(directory, ["python3", "/scenario/oracle.py", "/final"],
                  binds=[(source, "/scenario"), (final, "/final")], env={"PATH": path},
                  capture_output=True, text=True, timeout=1800)
  (directory / "oracle.log").write_text(g.stdout + "\n--- stderr\n" + g.stderr)
  return g


def regrade(args):
  """Grades every finished run again, keeping the previous outcome as `success_before`."""
  records = [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]
  for r in records:
    if args.only and r["scenario"] != args.only:
      continue
    directory = RUNS / r["id"]
    g = grade(directory, scenario_dir(r["scenario"]), directory / "final")
    r.setdefault("success_before", r["success"])
    r["success"], r["oracle_tail"] = g.returncode == 0, (g.stdout + g.stderr)[-1500:]
    print(f"{r['id']}: {r['success_before']} -> {r['success']}", flush=True)
  RESULTS.write_text("".join(json.dumps(r) + "\n" for r in records))


def run(args):
  data = json.loads(PLAN.read_text())
  todo = [r for r in data["runs"] if r["id"] not in done_ids()
          and (not args.only or r["scenario"] == args.only)
          and r["scenario"] not in (args.exclude or [])]
  print(f"{len(todo)} runs to execute", flush=True)

  def work(r):
    print(f"[{r['id']}] start", flush=True)
    try:
      record = execute(r, dry=args.dry)
    except Exception as e:
      print(f"[{r['id']}] harness error: {e!r}", flush=True)
      return
    if record is None:
      return
    with lock:
      with open(RESULTS, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[{r['id']}] done: success={record['success']} turns={record['num_turns']} "
          f"pmdb={record['pmdb_calls']}+{record['pmdb_record_calls']} wall={record['wall_seconds']}s",
          flush=True)

  with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool:
    list(pool.map(work, todo))


def status(args):
  data = json.loads(PLAN.read_text())
  print(f"{len(done_ids())}/{len(data['runs'])} done")


def main():
  parser = argparse.ArgumentParser()
  sub = parser.add_subparsers(dest="command", required=True)
  sub.add_parser("plan")
  r = sub.add_parser("run")
  r.add_argument("--parallel", type=int, default=8)
  r.add_argument("--only")
  r.add_argument("--exclude", action="append")
  r.add_argument("--dry", action="store_true")
  sub.add_parser("status")
  g = sub.add_parser("regrade")
  g.add_argument("--only")
  args = parser.parse_args()
  {"plan": plan, "run": run, "status": status, "regrade": regrade}[args.command](args)


if __name__ == "__main__":
  main()
