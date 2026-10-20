"""Access to the exercise programs: their sources, input generators and execution."""

import importlib.util
import json
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
from pmdbbench.execution import run

ROOT = Path(__file__).resolve().parent.parent
PROGRAMS = ROOT / "programs"
NAMES = ["warehouse", "sheet", "league"]

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
  return "input.txt" if isinstance(generator(name)(0), str) else "input.json"


if __name__ == "__main__":
  # Smoke test: every program runs cleanly on generated inputs.
  for name in NAMES:
    crashes = [s for s in range(100) if run(PROGRAMS / name, input_text(name, s))[0] != 0]
    print(f"{name}: {len(crashes)} crashes in 100 inputs {crashes[:5]}")
    print("".join(run(PROGRAMS / name, input_text(name, 3))[1].splitlines(True)[:5]))
