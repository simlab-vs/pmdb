"""Generates mutants of the exercise programs and measures their runtime features.

Mutation sites are enumerated mechanically inside function bodies and sampled with a fixed seed,
so that no person or model chooses where bugs go. Each mutant is run on generated inputs and
compared with the original program, which serves as the oracle.

Usage: python3 mutate.py [--inputs N] [--sites N] > mutants.json
"""

import argparse
import ast
import copy
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import programs

SEED = 20261001

COMPARE_SWAPS = {
  ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
  ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
BINOP_SWAPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.FloorDiv: ast.Mod, ast.Mod: ast.FloorDiv}
BOOLOP_SWAPS = {ast.And: ast.Or, ast.Or: ast.And}


def enclosing_functions(tree):
  """Maps the id of every node inside a function body to the qualified name of that function."""
  owners = {}

  def visit(node, scope):
    for child in ast.iter_child_nodes(node):
      if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
        name = f"{scope}.{child.name}" if scope else child.name
        for n in ast.walk(child):
          owners.setdefault(id(n), name)
        visit(child, name)
      elif isinstance(child, ast.ClassDef):
        visit(child, f"{scope}.{child.name}" if scope else child.name)
      else:
        visit(child, scope)

  visit(tree, "")
  return owners


def inside_fstring(tree):
  ids = set()
  for node in ast.walk(tree):
    if isinstance(node, ast.JoinedStr):
      ids.update(id(n) for n in ast.walk(node))
  return ids


def sites(source):
  """Returns the mutation sites of `source` as `(node index, operator, description)` triples."""
  tree = ast.parse(source)
  owners = enclosing_functions(tree)
  excluded = inside_fstring(tree)
  result = []
  for index, node in enumerate(ast.walk(tree)):
    if id(node) not in owners or id(node) in excluded or not hasattr(node, "lineno"):
      continue
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE_SWAPS:
      result.append((index, "compare", f"{type(node.ops[0]).__name__} -> "
                     f"{COMPARE_SWAPS[type(node.ops[0])].__name__}"))
    elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_SWAPS:
      result.append((index, "binop", f"{type(node.op).__name__} -> "
                     f"{BINOP_SWAPS[type(node.op)].__name__}"))
    elif isinstance(node, ast.BoolOp):
      result.append((index, "boolop", f"{type(node.op).__name__} -> "
                     f"{BOOLOP_SWAPS[type(node.op)].__name__}"))
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
      result.append((index, "drop-not", "not x -> x"))
    elif (isinstance(node, ast.Constant) and type(node.value) is int):
      result.append((index, "const+1", f"{node.value} -> {node.value + 1}"))
      result.append((index, "const-1", f"{node.value} -> {node.value - 1}"))
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
      if node.func.id in ("min", "max"):
        result.append((index, "minmax", f"{node.func.id} -> {'max' if node.func.id == 'min' else 'min'}"))
      elif len(node.args) >= 2 and not any(isinstance(a, ast.Starred) for a in node.args):
        result.append((index, "swap-args", f"swap arguments of {node.func.id}"))
  return result


def mutated_node(node, operator):
  node = copy.deepcopy(node)
  if operator == "compare":
    node.ops = [COMPARE_SWAPS[type(node.ops[0])]()]
  elif operator == "binop":
    node.op = BINOP_SWAPS[type(node.op)]()
  elif operator == "boolop":
    node.op = BOOLOP_SWAPS[type(node.op)]()
  elif operator == "drop-not":
    node = node.operand
  elif operator == "const+1":
    node.value += 1
  elif operator == "const-1":
    node.value -= 1
  elif operator == "minmax":
    node.func.id = "max" if node.func.id == "min" else "min"
  elif operator == "swap-args":
    node.args[0], node.args[1] = node.args[1], node.args[0]
  return node


def apply(source, index, operator):
  """Returns `(mutated source, function, line)`, changing only the text of the mutated node."""
  tree = ast.parse(source)
  owners = enclosing_functions(tree)
  node = list(ast.walk(tree))[index]
  replacement = ast.unparse(mutated_node(node, operator))
  if isinstance(node, ast.Constant) and node.value < 0 or operator == "drop-not":
    replacement = f"({replacement})" if operator != "drop-not" else replacement

  lines = source.splitlines(keepends=True)
  offsets = [0]
  for l in lines:
    offsets.append(offsets[-1] + len(l.encode()))
  data = source.encode()
  start = offsets[node.lineno - 1] + node.col_offset
  end = offsets[node.end_lineno - 1] + node.end_col_offset
  original = data[start:end].decode()
  if original.startswith("(") and not replacement.startswith("("):
    replacement = f"({replacement})"
  mutated = (data[:start] + replacement.encode() + data[end:]).decode()
  ast.parse(mutated)
  return mutated, owners[id(node)], node.lineno, original, replacement


# Runs a program on many inputs in one process. Executed in a subprocess per mutant.
RUNNER = r"""
import contextlib, io, json, os, sys, traceback
directory, inputs_dir, count = sys.argv[1], sys.argv[2], int(sys.argv[3])
sys.path.insert(0, directory)
os.chdir(directory)
sys.setrecursionlimit(3000)
import main
results = []
for i in range(count):
  out = io.StringIO()
  error = None
  try:
    with contextlib.redirect_stdout(out):
      main.main(os.path.join(inputs_dir, str(i)))
  except BaseException as e:
    error = "".join(traceback.format_exception(e))[-3000:]
  results.append([out.getvalue(), error])
json.dump(results, sys.stdout)
"""


def run_all(directory, inputs_dir, count, timeout=120):
  r = subprocess.run(
    [sys.executable, "-c", RUNNER, str(directory), str(inputs_dir), str(count)],
    capture_output=True, text=True, timeout=timeout, env={"PYTHONDONTWRITEBYTECODE": "1",
                                                          "PYTHONHASHSEED": "0", "PATH": ""})
  return json.loads(r.stdout)


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
