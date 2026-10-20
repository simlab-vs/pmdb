"""Materializes exercises: mutated sources, the reported input and the expected output."""

import json
import shutil
from pathlib import Path

import mutate
import programs
from pmdbbench.execution import run_all


def load(path):
  return {e["id"]: e for e in json.load(open(path))}


def write_sources(exercise, directory):
  """Writes the mutated sources of `exercise` into `directory`."""
  directory.mkdir(parents=True, exist_ok=True)
  for p in programs.sources(exercise["program"]):
    text = p.read_text()
    if p.name == exercise["file"]:
      text, function, line, original, replacement = mutate.apply(
        text, exercise["site"], exercise["operator"], exercise["argument"])
      assert (function, line, original) == (exercise["function"], exercise["line"],
                                           exercise["original"]), exercise["id"]
    (directory / p.name).write_text(text)


def materialize(exercise, directory):
  """Writes everything an agent sees for `exercise` into `directory`."""
  write_sources(exercise, directory)
  name = programs.input_file_name(exercise["program"])
  text = programs.input_text(exercise["program"], exercise["report_seed"])
  (directory / name).write_text(text)
  status, expected, _ = programs.run(programs.PROGRAMS / exercise["program"], text)
  assert status == 0
  (directory / "expected_output.txt").write_text(expected)
  status, actual, _ = programs.run(directory, text)
  assert (status, actual) != (0, expected), f"{exercise['id']} does not fail on its input"
  return name


def grade(exercise, directory, inputs=300):
  """Returns how the program in `directory` compares with the oracle.

  The result has `reported_ok` (the reported input now gives the expected output) and
  `generated_failures` (how many of the generated inputs still differ from the oracle).
  """
  import tempfile
  name = exercise["program"]
  with tempfile.TemporaryDirectory() as t:
    work = Path(t) / "program"
    work.mkdir()
    for p in programs.sources(name):
      candidate = directory / p.name
      if candidate.exists():
        shutil.copy(candidate, work / p.name)
    inputs_dir = Path(t) / "inputs"
    inputs_dir.mkdir()
    seeds = list(range(inputs)) + [exercise["report_seed"]]
    for i, s in enumerate(seeds):
      (inputs_dir / str(i)).write_text(programs.input_text(name, s))
    oracle = run_all(programs.PROGRAMS / name, inputs_dir, len(seeds))
    try:
      results = run_all(work, inputs_dir, len(seeds), timeout=300)
    except Exception as e:
      return {"reported_ok": False, "generated_failures": inputs, "error": repr(e)}
  differs = [r != o for r, o in zip(results, oracle)]
  return {"reported_ok": not differs[-1], "generated_failures": sum(differs[:-1])}
