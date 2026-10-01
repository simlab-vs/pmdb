"""Lists every pmdb command agents ran, with the output they saw.

Usage: python3 pmdb_attempts.py [runs directory] > attempts.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def attempts(run_dir):
  """Yields `(command, output, is_error)` for each Bash call mentioning pmdb in a transcript."""
  commands = {}
  path = run_dir / "transcript.jsonl"
  for line in path.read_text().splitlines():
    try:
      event = json.loads(line)
    except json.JSONDecodeError:
      continue
    content = event.get("message", {}).get("content", [])
    if not isinstance(content, list):
      continue
    for block in content:
      if block.get("type") == "tool_use":
        tool_input = block.get("input", {})
        text = tool_input.get("command", "") or tool_input.get("file_path", "")
        if "pmdb" in text:
          commands[block["id"]] = (block.get("name"), text)
      elif block.get("type") == "tool_result" and block.get("tool_use_id") in commands:
        output = block.get("content")
        if isinstance(output, list):
          output = "\n".join(c.get("text", "") for c in output if isinstance(c, dict))
        tool, command = commands.pop(block["tool_use_id"])
        yield tool, command, output or "", bool(block.get("is_error"))


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
