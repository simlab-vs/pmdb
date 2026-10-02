"""Running exercise programs, whose entry point is a function `main(path)` in `main.py`."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

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
