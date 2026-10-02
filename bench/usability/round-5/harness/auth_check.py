"""Checks that Claude Code can authenticate inside the offline sandbox, through the API relay.

Usage: python3 auth_check.py
"""

import json
import tempfile
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs
import offline
from pmdbbench.credentials import token


def main():
  bugs.TMP.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(dir=bugs.TMP) as t:
    root = Path(t)
    (root / "home").mkdir()
    (root / "work").mkdir()
    offline.prepare_etc(root)
    secret = token()
    r = offline.run(root, [
      "claude", "-p", "Reply with the single word: ready", "--model", "haiku",
      "--output-format", "json", "--max-turns", "1", "--tools", "", "--strict-mcp-config",
      "--setting-sources", ""], env={"CLAUDE_CODE_OAUTH_TOKEN": secret}, api=True,
      capture_output=True, text=True, timeout=150)
    try:
      d = json.loads(r.stdout)
      print({k: d.get(k) for k in ("is_error", "result", "num_turns", "subtype")},
            "models:", list((d.get("modelUsage") or {}).keys()))
    except json.JSONDecodeError:
      print("exit", r.returncode, (r.stdout + r.stderr).replace(secret, "<token>")[-1500:])


if __name__ == "__main__":
  main()
