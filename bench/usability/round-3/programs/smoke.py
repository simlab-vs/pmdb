"""Smoke test of the round-3 programs: runs each on many generated inputs.

For every program and seed, the generated input is written to a temporary directory and `main` is
imported fresh and run on it. Reports crashes, run times, the number of distinct outputs and the
size of the sources.

Usage: python3 smoke.py [number of seeds, default 300] [program...]
"""

import ast
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ["warehouse", "sheet", "league"]
TIME_LIMIT = 0.5


def load_module(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def write_input(directory, data):
  if isinstance(data, str):
    path = Path(directory) / "input.txt"
    path.write_text(data)
  else:
    path = Path(directory) / "input.json"
    path.write_text(json.dumps(data, indent=1) + "\n")
  return path


def run_fresh(program_dir, input_path):
  """Imports the program's modules afresh and runs its main; returns (output, seconds)."""
  modules = [p.stem for p in program_dir.glob("*.py")]
  for module in modules:
    sys.modules.pop(module, None)
  sys.path.insert(0, str(program_dir))
  try:
    main = importlib.import_module("main")
    out = io.StringIO()
    start = time.perf_counter()
    with contextlib.redirect_stdout(out):
      main.main(str(input_path))
    return out.getvalue(), time.perf_counter() - start
  finally:
    sys.path.remove(str(program_dir))
    for module in modules:
      sys.modules.pop(module, None)


def source_stats(program_dir):
  """Returns (lines without gen.py, number of functions and methods, per-file line counts)."""
  per_file = {}
  functions = 0
  for path in sorted(program_dir.glob("*.py")):
    text = path.read_text()
    per_file[path.name] = len(text.splitlines())
    if path.name != "gen.py":
      functions += sum(isinstance(node, ast.FunctionDef) for node in ast.walk(ast.parse(text)))
  lines = sum(n for name, n in per_file.items() if name != "gen.py")
  return lines, functions, per_file


def check(name, seeds):
  program_dir = ROOT / name
  generate = load_module(f"gen_{name}", program_dir / "gen.py").generate
  crashes = []
  outputs = set()
  times = []
  output_lines = []
  with tempfile.TemporaryDirectory() as directory:
    for seed in range(seeds):
      path = write_input(directory, generate(seed))
      try:
        output, seconds = run_fresh(program_dir, path)
      except Exception:
        crashes.append((seed, traceback.format_exc().strip().splitlines()[-1]))
        continue
      outputs.add(output)
      times.append(seconds)
      output_lines.append(len(output.splitlines()))

  lines, functions, per_file = source_stats(program_dir)
  print(f"== {name}")
  print(f"  sources: {lines} lines without gen.py, {functions} functions; "
        + ", ".join(f"{f} {n}" for f, n in per_file.items()))
  print(f"  {seeds} inputs: {len(crashes)} crashes, {len(outputs)} distinct outputs")
  if times:
    slow = sum(1 for t in times if t > TIME_LIMIT)
    print(f"  time: mean {sum(times) / len(times) * 1000:.1f} ms, max {max(times) * 1000:.1f} ms, "
          f"{slow} over {TIME_LIMIT} s")
    print(f"  output lines: min {min(output_lines)}, max {max(output_lines)}")
  for seed, error in crashes[:10]:
    print(f"  crash seed {seed}: {error}")
  return not crashes


def main(argv):
  seeds = int(argv[0]) if argv else 300
  names = argv[1:] or NAMES
  ok = all([check(name, seeds) for name in names])
  print("OK" if ok else "FAILED")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
