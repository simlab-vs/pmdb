"""Generates mutants of the exercise programs and measures their runtime features.

Mutation sites are enumerated mechanically inside function bodies, with round 1's operators and
the realistic operators of `realistic.py`. Since some operators have many more sites than others
(every variable read is a `wrong-var` site), up to `--per-operator` sites are sampled per operator
and program, with a fixed seed, so that no person or model chooses where bugs go. Each mutant is
run on generated inputs and compared with the original program, which serves as the oracle.

Usage: python3 mutate.py [--inputs N] [--per-operator N] > mutants.json
"""

import argparse
import collections
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import programs
from pmdbbench.execution import run_all
from realistic import apply, sites

SEED = 20261002


def changed_lines(actual, expected):
  """Returns the number of lines of `expected` that differ in `actual`, by position."""
  a, e = actual.splitlines(), expected.splitlines()
  return sum(x != y for x, y in zip(a, e)) + abs(len(a) - len(e))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--inputs", type=int, default=300)
  parser.add_argument("--per-operator", type=int, default=8,
                      help="sites sampled per operator and program")
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

      by_operator = collections.defaultdict(list)
      for p in programs.sources(name):
        for s in sites(p.read_text()):
          by_operator[s[1]].append((p, s))
      sample = []
      for operator in sorted(by_operator):
        candidates = by_operator[operator]
        sample += rng.sample(candidates, min(args.per_operator, len(candidates)))
      print(f"{name}: {sum(map(len, by_operator.values()))} sites, sampling {len(sample)}",
            file=sys.stderr)

      for path, (index, operator, argument, description) in sample:
        source = path.read_text()
        try:
          mutated, function, line, original, replacement = apply(source, index, operator, argument)
        except SyntaxError:
          continue
        if mutated == source:
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
          "operator": operator, "argument": argument, "description": description,
          "original": original, "replacement": replacement, "site": index,
          "fail_rate": len(failing) / args.inputs, "crash_rate": len(crashes) / args.inputs,
          "report_seed": first,
          "report_crashes": first is not None and results[first][1] is not None,
          "report_changed_lines": None if first is None else changed_lines(
            results[first][0], oracle[first][0]),
          "report_output_lines": None if first is None else len(oracle[first][0].splitlines()),
        })
  json.dump(mutants, sys.stdout, indent=1)


if __name__ == "__main__":
  main()
