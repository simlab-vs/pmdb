"""Access to the exercise programs: their sources, input generators and execution."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRAMS = ROOT / "programs"
NAMES = ["invoicing", "calc", "scheduler", "routes"]

# Files of a program that are not part of what agents see.
HIDDEN = {"gen.py"}


def sources(name):
  """Returns the paths of the source files of program `name` that agents see."""
  return sorted(p for p in (PROGRAMS / name).glob("*.py") if p.name not in HIDDEN)


def generator(name):
  spec = importlib.util.spec_from_file_location(f"gen_{name}", PROGRAMS / name / "gen.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module.generate


def input_text(name, seed):
  """Returns the contents of the input file generated for program `name` with `seed`."""
  data = generator(name)(seed)
  return data if isinstance(data, str) else json.dumps(data, indent=1) + "\n"


def input_file_name(name):
  return "input.txt" if name == "calc" else "input.json"


def run(directory, input_text, timeout=20):
  """Runs the program in `directory` on `input_text`, returning `(returncode, stdout, stderr)`."""
  with tempfile.TemporaryDirectory() as t:
    path = Path(t) / "input"
    path.write_text(input_text)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    try:
      r = subprocess.run(
        [sys.executable, "main.py", str(path)], cwd=directory, capture_output=True, text=True,
        timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
      return ("timeout", "", "")
    return (r.returncode, r.stdout, r.stderr)


if __name__ == "__main__":
  # Smoke test: every program runs cleanly on generated inputs.
  for name in NAMES:
    crashes = [s for s in range(100) if run(PROGRAMS / name, input_text(name, s))[0] != 0]
    print(f"{name}: {len(crashes)} crashes in 100 inputs {crashes[:5]}")
    print("".join(run(PROGRAMS / name, input_text(name, 3))[1].splitlines(True)[:5]))
