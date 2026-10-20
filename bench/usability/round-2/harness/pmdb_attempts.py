"""Lists every pmdb command agents ran, with the output they saw.

Usage: python3 pmdb_attempts.py [runs directory] > attempts.json
"""

import json
import sys
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
from pmdbbench.transcripts import attempts

ROOT = Path(__file__).resolve().parent.parent


def main():
  positional = [a for a in sys.argv[1:] if not a.startswith("--")]
  runs = Path(positional[0]) if positional else ROOT / "_work" / "runs"
  result = []
  for run_dir in sorted(p for p in runs.iterdir() if (p / "transcript.jsonl").exists()
                        and "-B-" in p.name and ".interrupted" not in p.name):
    for i, (tool, command, output, error) in enumerate(attempts(run_dir)):
      result.append({"run": run_dir.name, "step": i, "tool": tool, "command": command,
                     "is_error": error, "output": output[:1500],
                     "output_lines": output.count("\n") + 1})
  if "--markdown" in sys.argv:
    print("# Every pmdb command agents ran\n")
    print("Extracted from the transcripts by `harness/pmdb_attempts.py`. Reads of the README are "
          "omitted; output is cut to its first two lines.\n")
    for x in result:
      if x["tool"] != "Bash":
        continue
      lines = [l for l in x["output"].strip().splitlines() if l.strip()][:2]
      shown = "\n".join(lines) + (f"\n… ({x['output_lines']} lines)" if x["output_lines"] > 2 else "")
      print(f"**{x['run']}**, step {x['step']}\n\n```\n$ {x['command'].strip()}\n{shown}\n```\n")
  else:
    json.dump(result, sys.stdout, indent=1)


if __name__ == "__main__":
  main()
