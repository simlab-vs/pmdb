"""Checks that Claude Code can authenticate inside the sandbox. Usage: python3 auth_check.py"""

import json
import subprocess
import tempfile
from pathlib import Path

import run_study
import sandbox


def main():
  with tempfile.TemporaryDirectory() as t:
    root = Path(t)
    (root / "home").mkdir()
    (root / "work").mkdir()
    sandbox.prepare_etc(root)
    secret = run_study.token()
    r = subprocess.run(sandbox.command(root, [
      "claude", "-p", "Reply with the single word: ready", "--model", "haiku",
      "--output-format", "json", "--max-turns", "1", "--tools", "", "--strict-mcp-config",
      "--setting-sources", ""], env={"CLAUDE_CODE_OAUTH_TOKEN": secret}),
      capture_output=True, text=True, timeout=150)
    try:
      d = json.loads(r.stdout)
      print({k: d.get(k) for k in ("is_error", "result", "num_turns", "subtype")},
            "models:", list((d.get("modelUsage") or {}).keys()))
    except json.JSONDecodeError:
      print("exit", r.returncode, (r.stdout + r.stderr).replace(secret, "<token>")[-1500:])


if __name__ == "__main__":
  main()
