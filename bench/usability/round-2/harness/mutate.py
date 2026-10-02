"""Generates mutants of the exercise programs and measures their runtime features.

Mutation sites are enumerated mechanically inside function bodies and sampled with a fixed seed,
so that no person or model chooses where bugs go. Each mutant is run on generated inputs and
compared with the original program, which serves as the oracle.

Usage: python3 mutate.py [--inputs N] [--sites N] > mutants.json
"""

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import programs
from pmdbbench.execution import RUNNER, run_all  # noqa: F401
from pmdbbench.mutation import (  # noqa: F401
  BINOP_SWAPS, BOOLOP_SWAPS, COMPARE_SWAPS, apply, enclosing_functions, inside_fstring,
  mutated_node, sites)

SEED = 20261001

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--inputs", type=int, default=300)
  parser.add_argument("--sites", type=int, default=60, help="sites sampled per program")
  args = parser.parse_args()

  rng = random.Random(SEED)
  mutants = []
  for name in programs.NAMES:
    with tempfile.TemporaryDirectory() as t:
      inputs_dir = Path(t) / "inputs"
      inputs_dir.mkdir()
      for i in range(args.inputs):
        (inputs_dir / str(i)).write_text(programs.input_text(name, i))
      oracle = run_all(programs.PROGRAMS / name, inputs_dir, args.inputs)
      assert all(e is None for _, e in oracle), f"{name}: the original program fails"

      candidates = [(p, s) for p in programs.sources(name) for s in sites(p.read_text())]
      sample = rng.sample(candidates, min(args.sites, len(candidates)))
      print(f"{name}: {len(candidates)} sites, sampling {len(sample)}", file=sys.stderr)

      for path, (index, operator, description) in sample:
        source = path.read_text()
        try:
          mutated, function, line, original, replacement = apply(source, index, operator)
        except SyntaxError:
          continue
        work = Path(t) / "mutant"
        work.mkdir(exist_ok=True)
        for p in programs.sources(name):
          (work / p.name).write_text(mutated if p == path else p.read_text())
        try:
          results = run_all(work, inputs_dir, args.inputs)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
          continue
        failing = [i for i, (r, o) in enumerate(zip(results, oracle)) if r != o]
        crashes = [i for i in failing if results[i][1] is not None]
        first = failing[0] if failing else None
        mutants.append({
          "program": name, "file": path.name, "function": function, "line": line,
          "operator": operator, "description": description,
          "original": original, "replacement": replacement, "site": index,
          "fail_rate": len(failing) / args.inputs, "crash_rate": len(crashes) / args.inputs,
          "report_seed": first,
          "report_crashes": first is not None and results[first][1] is not None,
          "report_traceback_names_function": (
            first is not None and results[first][1] is not None
            and function.split(".")[-1] in results[first][1]),
        })
  json.dump(mutants, sys.stdout, indent=1)


if __name__ == "__main__":
  main()
