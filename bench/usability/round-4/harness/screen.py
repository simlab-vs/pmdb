"""Screens the eligible bugs with an agent that can only read the code.

Every bug that `prepare.py` found eligible is screened once, in the order of
`data/prepared.jsonl` (there is no stopping rule). The agent (Claude Code with the model `MODEL`,
in the sandbox of the study's runs, without the bug's environment) gets the project as in the
study's runs, plus `/work/failing_tests.txt` holding pytest's output for the failing tests at the
parent's sources (recorded by `prepare.py`), and only the tools Read, Grep and Glob, so it can't
run anything. A bug is localized if the function named in the agent's `RESULT:` line is one of
the fix's functions, by the rule of `run_study.py` (`bugs.localized`).

Usage: python3 screen.py  (appends to ../_work/screen.jsonl; run it again to resume)
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs
from pmdbbench import sandbox
from pmdbbench.credentials import token
from pmdbbench.transcripts import claimed, parse_stream, scrub

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
OUT = WORK / "screen.jsonl"
MODEL = "sonnet"
TOOLS = "Read,Grep,Glob"
MAX_TURNS = 40
TIMEOUT = 15 * 60

PROMPT = """\
A user reported that tests of the Python project in /work fail. They ran

    python -m pytest -p no:randomly -q {tests}

in /work, and the tests fail. pytest's output is in /work/failing_tests.txt.

You can't run anything: find the root cause by reading the code. Don't modify any file. When you \
are done, end your reply with a line of the form

RESULT: {{"file": "<file with the bug>", "function": "<function with the bug>", "cause": "<one sentence>"}}
"""


def eligible():
  """Returns the eligible bugs: their records of `bugs.jsonl` and `prepared.jsonl`, merged."""
  mined = {b["id"]: b for b in bugs.load(ROOT / "data" / "bugs.jsonl")}
  return [dict(mined[p["id"]], **p) for p in bugs.load(ROOT / "data" / "prepared.jsonl")
          if p["status"] == "eligible"]


def screen(bug):
  directory = WORK / "screen" / bug["id"]
  if directory.exists():
    shutil.rmtree(directory)
  bugs.materialize(bug, directory, env=False)
  (directory / "work" / "failing_tests.txt").write_text(bug["failing_output"])
  prompt = PROMPT.format(tests=bugs.shell_ids(bug, bug["failing_tests"]))
  (directory / "prompt.txt").write_text(prompt)
  secret = token()
  transcript = directory / "transcript.jsonl"
  timed_out = False
  with open(transcript, "w") as out:
    try:
      subprocess.run(sandbox.command(directory, [
        "claude", "-p", prompt, "--model", MODEL,
        "--output-format", "stream-json", "--verbose", "--max-turns", str(MAX_TURNS),
        "--tools", TOOLS, "--allowedTools", TOOLS, "--permission-mode", "dontAsk",
        "--strict-mcp-config", "--setting-sources", ""], env={"CLAUDE_CODE_OAUTH_TOKEN": secret}),
        stdout=out, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
      timed_out = True
  scrub(transcript, secret)
  metrics = parse_stream(transcript)
  result = metrics["result"] or {}
  claim = claimed(result.get("result"))
  return {"bug": bug["id"], "repo": bug["repo"], "fix_functions": bug["fix_functions"],
          "claim": claim, "localized": bugs.localized(claim, bug["fix_functions"]),
          # Running out of turns or time without naming a function counts as not localizing it.
          "complete": timed_out or result.get("subtype") == "error_max_turns" or (
            bool(metrics["result"]) and not result.get("is_error")),
          "timed_out": timed_out, "subtype": result.get("subtype"),
          "num_turns": result.get("num_turns"), "usage": result.get("usage"),
          "duration_ms": result.get("duration_ms"), "model": metrics["model"]}


def main():
  done = set()
  if OUT.exists():
    done = {json.loads(l)["bug"] for l in OUT.read_text().splitlines() if l.strip()}
  for bug in eligible():
    if bug["id"] in done:
      continue
    s = screen(bug)
    if not s["complete"]:
      sys.exit(f"{bug['id']}: the screening run did not complete; run again later")
    with open(OUT, "a") as f:
      f.write(json.dumps(s) + "\n")
    print(f"{bug['id']} ({', '.join(bug['fix_functions'])}): "
          f"{'localized' if s['localized'] else 'not localized'}, claimed {s['claim']}", flush=True)


if __name__ == "__main__":
  main()
