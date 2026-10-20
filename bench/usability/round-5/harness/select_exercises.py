"""Selects round 5's exercises from the screened eligible bugs with a fixed, pre-registered rule.

1. The repositories of the eligible bugs, and each repository's bugs (in the order of
   `prepared.jsonl`), are put in an order drawn with the seed `SEED`.
2. Bugs the screen did not localize ("hard") are taken first: cycling over the repositories in
   their order, each cycle takes the next hard bug of each repository that has fewer than
   `PER_REPO` exercises, until there are `COUNT` exercises or no hard bug can be taken.
3. Then localized bugs ("easy") are taken in the same way.
4. The pilot bug is the bug the same procedure would take next, or, if the cap per repository
   leaves none, the first remaining eligible bug in the order of step 1.
5. If fewer than `COUNT` + 1 bugs are eligible, every eligible bug is an exercise (in the order of
   steps 2-3, then any left by the cap per repository), and the pilot reuses the first exercise
   (noted in the output as `pilot_reuses`).

Every eligible bug must have been screened. Whether the screen localized a bug is decided from
its claim with `bugs.localized`.

Usage: python3 select_exercises.py ../data/prepared.jsonl ../_work/screen.jsonl > ../_work/exercises.json
"""

import json
import random
import sys
from pathlib import Path

import bugs

SEED = 20261004  # round 4's
COUNT = 10
PER_REPO = 2
ROOT = Path(__file__).resolve().parent.parent


def sequence(queues, order, per_repo=PER_REPO):
  """Yields the bugs in the order the rule takes them, without a limit on their number."""
  taken = []
  for category in ("hard", "easy"):
    while True:
      progress = False
      for repo in order:
        if sum(t["repo"] == repo for t in taken) >= per_repo:
          continue
        queue = [b for b in queues[repo] if b["screen"] == category and b not in taken]
        if queue:
          taken.append(queue[0])
          progress = True
          yield queue[0]
      if not progress:
        break


def main(prepared_path, screen_path):
  mined = {b["id"]: b for b in bugs.load(ROOT / "data" / "bugs.jsonl")}
  texts = bugs.issues()
  prepared = [p for p in bugs.load(prepared_path) if p["status"] == "eligible"]
  screened = {s["bug"]: s for s in bugs.load(screen_path)}
  missing = [p["id"] for p in prepared if p["id"] not in screened]
  if missing:
    sys.exit(f"not screened: {missing}")

  rng = random.Random(SEED)
  repos = sorted({p["repo"] for p in prepared})
  rng.shuffle(repos)
  queues = {}
  for repo in repos:
    mine = [dict(mined[p["id"]], **p, bug=p["id"], issue=texts[p["id"]],
                 screen="easy" if bugs.localized(screened[p["id"]]["claim"],
                                                 p["fix_functions"]) else "hard",
                 screen_claim=screened[p["id"]]["claim"])
            for p in prepared if p["repo"] == repo]
    rng.shuffle(mine)
    queues[repo] = mine

  pilot_reuses = None
  if len(prepared) > COUNT:
    taken = list(sequence(queues, repos))
    chosen = taken[:COUNT]
    if len(taken) > COUNT:
      pilot = taken[COUNT]
    else:
      remaining = [b for r in repos for b in queues[r] if b not in chosen]
      pilot = remaining[0] if remaining else None
  else:
    taken = list(sequence(queues, repos))
    chosen = taken + [b for r in repos for b in queues[r] if b not in taken]
    pilot = chosen[0] if chosen else None
    pilot_reuses = pilot["bug"] if pilot else None
  if pilot is None:
    sys.exit("no bug left for the pilot")

  for i, b in enumerate(chosen):
    b["category"] = b["screen"]
    b["id"] = f"ex{i + 1:02d}-{b['bug']}-{b['screen']}"
  pilot = dict(pilot, category="pilot", id=f"pilot-{pilot['bug']}")
  json.dump({"seed": SEED, "repositories": repos, "exercises": chosen, "pilot": pilot,
             "pilot_reuses": pilot_reuses}, sys.stdout, indent=1)
  print(f"selected {len(chosen)} exercises "
        f"({sum(b['screen'] == 'hard' for b in chosen)} hard) and the pilot {pilot['bug']}"
        + (" (reusing the first exercise: fewer than 11 eligible bugs)" if pilot_reuses else ""),
        file=sys.stderr)


if __name__ == "__main__":
  main(*sys.argv[1:])
