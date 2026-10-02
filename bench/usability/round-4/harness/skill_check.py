"""Checks the skills that Claude Code sees and may use in the sandbox of the pmdb arm.

Usage: python3 skill_check.py

It installs the assembled skill as in a run of the pmdb arm, prints the tools and skills listed
when Claude Code starts, and asks it to invoke two bundled skills and then the pmdb skill, printing
which invocations were allowed.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import run_study
from pmdbbench import sandbox
from pmdbbench.credentials import token

PROMPT = ("Invoke the skill `simplify` with the Skill tool, then the skill `verify`, then the skill "
          "`pmdb`. Then reply with one line per skill saying whether the invocation succeeded.")


def main():
  with tempfile.TemporaryDirectory() as t:
    root = Path(t)
    (root / "work").mkdir()
    shutil.copytree(run_study.SKILL, root / "home" / ".claude" / "skills" / "pmdb")
    sandbox.prepare_etc(root)
    secret = token()
    r = subprocess.run(sandbox.command(root, [
      "claude", "-p", PROMPT, "--model", "haiku", "--output-format", "stream-json", "--verbose",
      "--max-turns", "4", "--tools", run_study.TOOLS_B, "--allowedTools", run_study.ALLOWED_B,
      "--disallowedTools", run_study.DENIED_B, "--permission-mode", "dontAsk", "--strict-mcp-config",
      "--setting-sources", "user"],
      opt=run_study.OPT, env={"CLAUDE_CODE_OAUTH_TOKEN": secret, **run_study.ENV_B}),
      capture_output=True, text=True, timeout=300)
    for line in r.stdout.replace(secret, "<token>").splitlines():
      try:
        e = json.loads(line)
      except json.JSONDecodeError:
        continue
      if e.get("type") == "system" and e.get("subtype") == "init":
        print("tools:", e.get("tools"))
        print("skills:", e.get("skills"))
      for block in e.get("message", {}).get("content", []) if e.get("type") in (
          "assistant", "user") else []:
        if block.get("type") == "tool_use":
          print("call:", block.get("name"), json.dumps(block.get("input")))
        elif block.get("type") == "tool_result":
          print("  error:" if block.get("is_error") else "  ok:", str(block.get("content"))[:160])
      if e.get("type") == "result":
        print("result:", (e.get("result") or "")[:500])
    if r.returncode:
      print("exit", r.returncode, (r.stderr or "").replace(secret, "<token>")[-800:])


if __name__ == "__main__":
  main()
