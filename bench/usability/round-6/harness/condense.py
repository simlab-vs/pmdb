"""Writes a condensed, readable version of each run's transcript, for qualitative analysis.

Each step shows the agent's text, the tool call (shortened) and the start of its result.

Usage: python3 condense.py   (writes ../_work/condensed/<run id>.md)
"""

import json
from pathlib import Path

import behaviour

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"


def short(s, n):
  s = s.strip()
  return s if len(s) <= n else s[:n] + f" … [{len(s) - n} more characters]"


def condense(run_dir, record):
  lines = [f"# {record['id']}", "",
           f"model {record['model']}, arm {record['arm']}, success {record['success']}, "
           f"localized {record['localized']}, turns {record['num_turns']}, "
           f"wrote tests {record.get('wrote_tests')}, ran pmdb-record {record.get('ran_pmdb_record')}, "
           f"changed {', '.join(record.get('changed_files', []))}", "",
           "## Prompt", "", (run_dir / "prompt.txt").read_text(), "", "## Steps", ""]
  n = 0
  for line in (run_dir / "transcript.jsonl").read_text().splitlines():
    try:
      e = json.loads(line)
    except json.JSONDecodeError:
      continue
    content = e.get("message", {}).get("content", [])
    if not isinstance(content, list):
      continue
    for b in content:
      if e.get("type") == "assistant" and b.get("type") == "text" and b["text"].strip():
        lines += [f"> {short(b['text'], 1200)}", ""]
      elif b.get("type") == "tool_use":
        n += 1
        i = b["input"]
        call = i.get("command") or i.get("file_path") or i.get("pattern") or json.dumps(i)
        if b["name"] == "Edit":
          call = f"{i.get('file_path')}\n- {short(i.get('old_string', ''), 400)}\n+ {short(i.get('new_string', ''), 400)}"
        lines += [f"**{n}. {b['name']}**", "```", short(str(call), 800), "```"]
      elif b.get("type") == "tool_result":
        flag = " (error)" if b.get("is_error") else ""
        lines += [f"result{flag}:", "```", short(behaviour.text_of(b), 700), "```", ""]
  lines += ["## Final answer", "", short(((record.get("claim") and json.dumps(record["claim"])) or ""), 600),
            "", "## Feedback", "", "```", json.dumps(record.get("feedback"), indent=1), "```"]
  return "\n".join(lines)


def main():
  out = WORK / "condensed"
  out.mkdir(exist_ok=True)
  for l in (WORK / "results.jsonl").read_text().splitlines():
    if l.strip():
      r = json.loads(l)
      (out / f"{r['id']}.md").write_text(condense(WORK / "runs" / r["id"], r))


if __name__ == "__main__":
  main()
