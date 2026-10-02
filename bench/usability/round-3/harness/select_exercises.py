"""Selects exercises from the generated mutants with a fixed, pre-registered rule.

Step 1, `candidates`: the candidates are the mutants that
- fail silently on their reported input (wrong output, no exception);
- fail on at most 25% of the generated inputs;
- change at most a third of the lines of the output of the reported input;
- are in a function called at a depth of at least 3 in the reported run, counting `main` as 1.
They are listed per program in an order drawn with a fixed seed.

Step 2, `screen.py`: candidates are screened in that order by a read-only agent.

Step 3, `final`: per program, in the order of step 1, the candidates the screen did not localize
("hard") are taken first, then the others; exercises are taken from the programs in turn (in the
order of `programs.NAMES`) until there are 10.

Usage:
  python3 select_exercises.py candidates mutants.json > candidates.json
  python3 select_exercises.py final candidates.json screen.jsonl > exercises.json
"""

import functools
import json
import random
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import programs

SEED = 31337
COUNT = 10
MAX_FAIL_RATE = 0.25
MIN_DEPTH = 3
NS = {"pmdb": "https://hevs.ch/pmdb"}
ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent.parent
PMDB = ROOT / "_work" / "opt-pmdb" / "bin" / "pmdb"
RECORD = REPOSITORY / "skills" / "pmdb" / "scripts" / "pmdb-record"


def recorded_name(function):
  """Returns `function` as the recorder names it, without `<locals>`."""
  return function.replace(".<locals>", "")


@functools.cache
def depths(name, seed):
  """Returns the smallest call depth of each function in the run of program `name` on the input
  generated with `seed`, counting `main` as 1."""
  with tempfile.TemporaryDirectory() as t:
    work = Path(t)
    for p in programs.sources(name):
      (work / p.name).write_text(p.read_text())
    input_name = programs.input_file_name(name)
    (work / input_name).write_text(programs.input_text(name, seed))
    subprocess.run([sys.executable, str(RECORD), "-o", "t.pmdb", "main.py", input_name],
                   cwd=work, capture_output=True, check=True)
    xml = subprocess.run([str(PMDB), "--export-xml", "t.pmdb"], cwd=work, capture_output=True,
                         check=True).stdout
  result = {}

  def visit(call, depth):
    f = recorded_name(call.find("pmdb:function", NS).text)
    result[f] = min(result.get(f, depth), depth)
    children = call.find("pmdb:observations", NS)
    for c in children.findall("pmdb:call", NS) if children is not None else []:
      visit(c, depth + 1)

  root = ET.fromstring(xml).find("pmdb:observations/pmdb:call", NS)
  for c in root.find("pmdb:observations", NS).findall("pmdb:call", NS):
    visit(c, 0)  # The script's module-level code calls `main`, at depth 1.
  return result


def candidates(path):
  mutants = json.load(open(path))
  rng = random.Random(SEED)
  result = []
  for name in programs.NAMES:
    pool = [m for m in mutants if m["program"] == name and m["fail_rate"] > 0
            and not m["report_crashes"] and m["fail_rate"] <= MAX_FAIL_RATE
            and m["report_changed_lines"] * 3 <= m["report_output_lines"]]
    rng.shuffle(pool)
    for m in pool:
      d = depths(name, m["report_seed"]).get(recorded_name(m["function"]))
      if d is not None and d >= MIN_DEPTH:
        result.append(dict(m, depth=d))
  json.dump(result, sys.stdout, indent=1)


def final(candidates_path, screen_path):
  pool = json.load(open(candidates_path))
  screened = {}
  for line in open(screen_path):
    if line.strip():
      s = json.loads(line)
      screened[s["candidate"]] = s
  queues = {}
  for name in programs.NAMES:
    mine = [dict(m, candidate=i) for i, m in enumerate(pool) if m["program"] == name]
    tried = [m for m in mine if m["candidate"] in screened]
    hard = [m for m in tried if not screened[m["candidate"]]["localized"]]
    easy = [m for m in tried if screened[m["candidate"]]["localized"]]
    queues[name] = [dict(m, screen="hard") for m in hard] + [dict(m, screen="easy") for m in easy]
  chosen = []
  while len(chosen) < COUNT and any(queues.values()):
    for name in programs.NAMES:
      if queues[name] and len(chosen) < COUNT:
        chosen.append(queues[name].pop(0))
  for i, m in enumerate(chosen):
    m["category"] = m["screen"]
    m["id"] = f"ex{i + 1:02d}-{m['program']}-{m['screen']}"
  json.dump(chosen, sys.stdout, indent=1)


if __name__ == "__main__":
  {"candidates": candidates, "final": final}[sys.argv[1]](*sys.argv[2:])
