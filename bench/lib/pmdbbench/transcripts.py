"""Reading the stream-json transcripts of Claude Code runs."""

import json
import re


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


def pmdb_errors(path):
  """Returns the error messages printed by pmdb commands in the transcript at `path`."""
  if not path.exists():
    return []
  commands, errors = {}, []
  for line in path.read_text().splitlines():
    try:
      event = json.loads(line)
    except json.JSONDecodeError:
      continue
    content = event.get("message", {}).get("content", [])
    if not isinstance(content, list):
      continue
    for block in content:
      if block.get("type") == "tool_use" and block.get("name") == "Bash":
        command = block.get("input", {}).get("command", "")
        if "pmdb" in command:
          commands[block["id"]] = command
      elif block.get("type") == "tool_result" and block.get("tool_use_id") in commands:
        text = block.get("content")
        text = text if isinstance(text, str) else json.dumps(text)
        for m in re.findall(r"(?:error|warning): [^\n\"\\]+", text):
          errors.append((commands[block["tool_use_id"]], m))
  return errors


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
