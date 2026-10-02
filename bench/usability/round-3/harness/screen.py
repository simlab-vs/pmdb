"""Screens candidate exercises with an agent that can only read the code.

For each program, candidates are screened in the order of `candidates.json` until `HARD` of them
are not localized or `MAX_SCREENED` have been screened. The agent (Claude Code with the model
`MODEL`, in the same sandbox as the study's runs) gets the mutated program, the reported input,
the expected output and the actual output, and only the tools Read, Grep and Glob, so it can't
run anything. A candidate is localized if the function named in the agent's `RESULT:` line is the
mutated function, by the rule of `run_study.py`.

Usage: python3 screen.py candidates.json  (appends to ../_work/screen.jsonl)
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import exercises
import programs
from pmdbbench import sandbox
from pmdbbench.credentials import token
from pmdbbench.transcripts import claimed, parse_stream, scrub

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
OUT = WORK / "screen.jsonl"
MODEL = "sonnet"
TOOLS = "Read,Grep,Glob"
HARD = 4
MAX_SCREENED = 8
MAX_TURNS = 40
TIMEOUT = 15 * 60

PROMPT = """\
A user reported a problem with the Python program in /work. They ran

    python3 main.py {input}

and the output, in /work/actual_output.txt, does not match what they expected, in \
/work/expected_output.txt.

You can't run any program: find the root cause by reading the code. Don't modify any file. When \
you are done, end your reply with a line of the form

RESULT: {{"file": "<file with the bug>", "function": "<function with the bug>", "cause": "<one sentence>"}}
"""


def localized(claim, function):
  return bool(claim) and (str(claim.get("function", "")).split(".")[-1].split("(")[0]
                          == function.split(".")[-1])


def screen(candidate, m):
  directory = WORK / "screen" / f"{candidate:03d}"
  if directory.exists():
    shutil.rmtree(directory)
  for d in ("home", "work"):
    (directory / d).mkdir(parents=True)
  sandbox.prepare_etc(directory)
  exercise = dict(m, id=f"candidate-{candidate}")
  input_name = exercises.materialize(exercise, directory / "work")
  _, actual, _ = programs.run(directory / "work", (directory / "work" / input_name).read_text())
  (directory / "work" / "actual_output.txt").write_text(actual)
  secret = token()
  transcript = directory / "transcript.jsonl"
  with open(transcript, "w") as out:
    try:
      subprocess.run(sandbox.command(directory, [
        "claude", "-p", PROMPT.format(input=input_name), "--model", MODEL,
        "--output-format", "stream-json", "--verbose", "--max-turns", str(MAX_TURNS),
        "--tools", TOOLS, "--allowedTools", TOOLS, "--permission-mode", "dontAsk",
        "--strict-mcp-config", "--setting-sources", ""], env={"CLAUDE_CODE_OAUTH_TOKEN": secret}),
        stdout=out, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
      pass
  scrub(transcript, secret)
  metrics = parse_stream(transcript)
  result = metrics["result"] or {}
  claim = claimed(result.get("result"))
  return {"candidate": candidate, "program": m["program"], "function": m["function"],
          "operator": m["operator"], "claim": claim, "localized": localized(claim, m["function"]),
          "complete": bool(metrics["result"]) and not result.get("is_error"),
          "num_turns": result.get("num_turns"), "model": metrics["model"]}


def main(path):
  pool = json.load(open(path))
  done = {}
  if OUT.exists():
    for line in OUT.read_text().splitlines():
      s = json.loads(line)
      done[s["candidate"]] = s
  for name in programs.NAMES:
    mine = [i for i, m in enumerate(pool) if m["program"] == name]
    for i in mine:
      tried = [done[j] for j in mine if j in done]
      if sum(not s["localized"] for s in tried) >= HARD or len(tried) >= MAX_SCREENED:
        break
      if i in done:
        continue
      s = screen(i, pool[i])
      if not s["complete"]:
        sys.exit(f"candidate {i}: the screening run did not complete; run again later")
      done[i] = s
      with open(OUT, "a") as f:
        f.write(json.dumps(s) + "\n")
      print(f"{name} candidate {i} ({pool[i]['operator']} in {pool[i]['function']}): "
            f"{'localized' if s['localized'] else 'not localized'}", flush=True)


if __name__ == "__main__":
  main(sys.argv[1])
