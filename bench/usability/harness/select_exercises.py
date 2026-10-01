"""Selects exercises from the generated mutants with a fixed, pre-registered rule.

Per program:
- "rare": a random silent mutant (wrong output, no exception) failing on at most 10% of inputs, or
  the silent mutant with the lowest failure rate if there is none;
- "subtle": a random silent mutant failing on more than 10% and at most 90% of inputs.
Controls: a random crashing mutant from each of two randomly chosen programs.

Usage: python3 select_exercises.py mutants.json > exercises.json
"""

import json
import random
import sys

import programs

SEED = 1729


def main(path):
  mutants = json.load(open(path))
  rng = random.Random(SEED)
  chosen = []

  for name in programs.NAMES:
    silent = [m for m in mutants if m["program"] == name and m["fail_rate"] > 0
              and not m["report_crashes"]]
    rare = [m for m in silent if m["fail_rate"] <= 0.10]
    pick = rng.choice(rare) if rare else min(silent, key=lambda m: m["fail_rate"])
    chosen.append(dict(pick, category="rare"))
    subtle = [m for m in silent if 0.10 < m["fail_rate"] <= 0.90 and m is not pick]
    chosen.append(dict(rng.choice(subtle), category="subtle"))

  for name in rng.sample(programs.NAMES, 2):
    crashes = [m for m in mutants if m["program"] == name and m["report_crashes"]]
    chosen.append(dict(rng.choice(crashes), category="crash"))

  for i, m in enumerate(chosen):
    m["id"] = f"ex{i + 1:02d}-{m['program']}-{m['category']}"
  json.dump(chosen, sys.stdout, indent=1)


if __name__ == "__main__":
  main(sys.argv[1])
