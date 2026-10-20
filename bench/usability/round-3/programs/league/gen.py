"""Generates random inputs for the league program (hidden from agents)."""

import random

NAMES = [
  "Ashford", "Bexley", "Carlow", "Dunmore", "Elmwood", "Fairport", "Glenrock", "Harwich",
  "Ivybridge", "Jarrow", "Kenmore", "Lisburn", "Marston", "Newbury", "Oakham", "Penrith",
  "Quarry", "Redhill", "Selby", "Thirsk", "Ulverston", "Valemouth", "Whitby", "Yarm",
]


def round_robin(teams):
  """Returns the rounds of a double round robin, as lists of (home, away)."""
  teams = list(teams)
  if len(teams) % 2:
    teams.append(None)
  n = len(teams)
  rounds = []
  for r in range(n - 1):
    pairs = []
    for i in range(n // 2):
      a, b = teams[i], teams[n - 1 - i]
      if a is not None and b is not None:
        pairs.append((a, b) if r % 2 == 0 else (b, a))
    rounds.append(pairs)
    teams = [teams[0]] + [teams[-1]] + teams[1:-1]
  return rounds + [[(b, a) for a, b in pairs] for pairs in rounds]


def goals(rng, attack):
  g = 0
  for _ in range(6):
    if rng.random() < attack:
      g += 1
  return g


def generate(seed):
  rng = random.Random(seed)
  pool = list(NAMES)
  rng.shuffle(pool)
  n_div = 3 if rng.random() < 0.1 else 2
  divisions = []
  for d in range(n_div):
    size = rng.randint(4, 6) if n_div == 3 else rng.randint(5, 8)
    teams = [pool.pop() for _ in range(size)]
    division = {"name": ["Premier", "Championship", "League One"][d], "teams": teams}
    divisions.append(division)
  for d in reversed(range(n_div)):
    if d > 0:
      divisions[d]["promote"] = rng.choice([1, 1, 2])
      roll = rng.random()
      divisions[d]["playoff"] = 4 if roll < 0.7 else 2 if roll < 0.9 else 8 if roll < 0.95 else 0
    if d < n_div - 1:
      below = divisions[d + 1]
      divisions[d]["relegate"] = below["promote"] + (1 if below["playoff"] >= 2 else 0)

  rules = {"away_goals": rng.random() < 0.5, "home_advantage": rng.choice([0, 40, 60, 60, 100]),
           "k": rng.choice([16, 20, 24, 32, 40])}
  if rng.random() < 0.1:
    rules["attack_bonus"] = rng.choice([3, 4])
  if rng.random() < 0.08:
    rules["close_loss_bonus"] = True
  if rng.random() < 0.05:
    rules["win"] = 2
  if rng.random() < 0.05:
    rules["red"] = 2

  strength = {t: rng.uniform(0.12, 0.38) for div in divisions for t in div["teams"]}
  skip_rate = 0.04 if rng.random() < 0.15 else 0.0
  forfeit = rng.random() < 0.06
  matches = []
  for division in divisions:
    for r, pairs in enumerate(round_robin(division["teams"]), start=1):
      for home, away in pairs:
        match = {"round": r, "home": home, "away": away,
                 "hg": goals(rng, strength[home] + 0.03), "ag": goals(rng, strength[away])}
        match["yh"] = rng.choice([0, 0, 1, 1, 2, 3])
        match["ya"] = rng.choice([0, 1, 1, 2, 2, 4])
        if rng.random() < 0.03:
          match["rh"] = 1
        if rng.random() < 0.03:
          match["ra"] = 1
        if skip_rate and rng.random() < skip_rate:
          match["status"] = rng.choice(["postponed", "abandoned"])
        matches.append(match)
  if forfeit:
    rng.choice(matches)["status"] = rng.choice(["forfeit_home", "forfeit_away"])
  rng.shuffle(matches)

  data = {"rules": rules, "divisions": divisions, "matches": matches}
  if rng.random() < 0.6:
    data["ratings"] = {t: rng.randint(1350, 1700) for t in strength if rng.random() < 0.8}
  if rng.random() < 0.08:
    team = rng.choice(list(strength))
    data["deductions"] = [{"team": team, "points": rng.choice([1, 3, 6, 9])}]

  scores = []
  for _ in range(rng.randint(1, 11) if rng.random() < 0.1 else 11):
    entry = [goals(rng, 0.2), goals(rng, 0.2)]
    if rng.random() < 0.5:
      p = rng.randint(2, 5)
      entry += [p, rng.choice([p - 1, p + 1, max(0, p - 2)])]
    scores.append(entry)
  data["playoff_scores"] = scores
  return data
