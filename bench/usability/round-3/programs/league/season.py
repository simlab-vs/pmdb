"""Records of the teams of a league season, built match by match from the fixtures.

A match counts for the table when it was played or forfeited; abandoned and postponed matches are
ignored. Points follow the competition rules, including the optional bonus points.
"""

DEFAULT_RULES = {
  "win": 3,
  "draw": 1,
  "loss": 0,
  "attack_bonus": None,
  "close_loss_bonus": False,
  "yellow": 1,
  "red": 3,
  "forfeit_score": [3, 0],
  "forfeit_penalty": 5,
  "forfeit_deduction": 1,
  "away_goals": False,
  "home_advantage": 60,
  "k": 24,
}

COUNTED_STATUSES = ("played", "forfeit_home", "forfeit_away")


def merge_rules(given):
  """Returns the competition rules, with defaults for those not given."""
  rules = dict(DEFAULT_RULES)
  rules.update(given or {})
  return rules


class Result:
  """The outcome of one match from the point of view of the table."""

  __slots__ = ("round", "home", "away", "hg", "ag", "status", "cards")

  def __init__(self, round_, home, away, hg, ag, status, cards):
    self.round = round_
    self.home = home
    self.away = away
    self.hg = hg
    self.ag = ag
    self.status = status
    self.cards = cards

  def is_forfeit(self):
    return self.status != "played"

  def winner(self):
    if self.hg > self.ag:
      return self.home
    if self.ag > self.hg:
      return self.away
    return None


def read_result(match, rules):
  """Turns a fixture entry into a Result, or returns None when it does not count."""
  status = match.get("status", "played")
  if status not in COUNTED_STATUSES:
    return None
  cards = {
    match["home"]: (match.get("yh", 0), match.get("rh", 0)),
    match["away"]: (match.get("ya", 0), match.get("ra", 0)),
  }
  hg, ag = match.get("hg", 0), match.get("ag", 0)
  if status == "forfeit_home":
    ag, hg = rules["forfeit_score"]
  elif status == "forfeit_away":
    hg, ag = rules["forfeit_score"]
  return Result(match.get("round", 0), match["home"], match["away"], hg, ag, status, cards)


def match_points(scored, conceded, rules):
  """Returns the points a team earns for a match it finished `scored`-`conceded`."""
  if scored > conceded:
    points = rules["win"]
  elif scored == conceded:
    points = rules["draw"]
  else:
    points = rules["loss"]
    if rules["close_loss_bonus"] and conceded - scored == 1:
      points += 1
  bonus = rules["attack_bonus"]
  if bonus is not None and scored >= bonus:
    points += 1
  return points


def card_points(yellows, reds, rules):
  return yellows * rules["yellow"] + reds * rules["red"]


class TeamRecord:
  """The accumulated record of one team in its division."""

  def __init__(self, name, division):
    self.name = name
    self.division = division
    self.played = 0
    self.won = 0
    self.drawn = 0
    self.lost = 0
    self.goals_for = 0
    self.goals_against = 0
    self.points = 0
    self.deducted = 0
    self.fair_play = 0
    self.clean_sheets = 0
    self.home_points = 0
    self.away_points = 0
    self.form = []

  def goal_difference(self):
    return self.goals_for - self.goals_against

  def total_points(self):
    return self.points - self.deducted

  def points_per_game(self):
    return self.total_points() / self.played if self.played else 0.0

  def add(self, scored, conceded, points, at_home):
    self.played += 1
    if at_home:
      self.home_points += points
    else:
      self.away_points += points
    if conceded == 0:
      self.clean_sheets += 1
    self.goals_for += scored
    self.goals_against += conceded
    self.points += points
    if scored > conceded:
      self.won += 1
      self.form.append("W")
    elif scored == conceded:
      self.drawn += 1
      self.form.append("D")
    else:
      self.lost += 1
      self.form.append("L")


class Season:
  """The divisions, team records and counted results of a season."""

  def __init__(self, divisions, rules):
    self.rules = rules
    self.divisions = []
    self.division_of = {}
    self.records = {}
    for division in divisions:
      self.divisions.append(dict(division))
      for team in division["teams"]:
        self.division_of[team] = division["name"]
        self.records[team] = TeamRecord(team, division["name"])
    self.results = []
    self.skipped = 0
    self.forfeits = 0

  def division(self, name):
    for division in self.divisions:
      if division["name"] == name:
        return division
    raise KeyError(name)

  def teams_in(self, name):
    return [self.records[team] for team in self.division(name)["teams"]]

  def results_in(self, name):
    return [r for r in self.results if self.division_of[r.home] == name]

  def record_match(self, match):
    """Adds one fixture to the records; returns the counted result or None."""
    result = read_result(match, self.rules)
    if result is None:
      self.skipped += 1
      return None
    home = self.records[result.home]
    away = self.records[result.away]
    home_points = match_points(result.hg, result.ag, self.rules)
    away_points = match_points(result.ag, result.hg, self.rules)
    if result.status == "forfeit_home":
      home_points = 0
    elif result.status == "forfeit_away":
      away_points = 0
    home.add(result.hg, result.ag, home_points, True)
    away.add(result.ag, result.hg, away_points, False)
    for record in (home, away):
      yellows, reds = result.cards[record.name]
      record.fair_play += card_points(yellows, reds, self.rules)
    if result.status == "forfeit_home":
      self.penalise_forfeit(home)
    elif result.status == "forfeit_away":
      self.penalise_forfeit(away)
    self.results.append(result)
    return result

  def penalise_forfeit(self, record):
    self.forfeits += 1
    record.fair_play += self.rules["forfeit_penalty"]
    record.deducted += self.rules["forfeit_deduction"]

  def apply_deductions(self, deductions):
    """Applies point deductions; a team's points may go negative."""
    for entry in deductions:
      record = self.records.get(entry["team"])
      if record is not None:
        record.deducted += entry["points"]


def division_summary(results):
  """Returns the home wins, draws, away wins and goals of a list of results played on the pitch."""
  summary = {"home": 0, "draw": 0, "away": 0, "goals": 0, "matches": 0}
  for result in results:
    if result.is_forfeit():
      continue
    summary["matches"] += 1
    summary["goals"] += result.hg + result.ag
    winner = result.winner()
    if winner is None:
      summary["draw"] += 1
    elif winner == result.home:
      summary["home"] += 1
    else:
      summary["away"] += 1
  return summary


def play_season(season, matches):
  """Records the fixtures in round order (keeping the file order within a round)."""
  ordered = sorted(enumerate(matches), key=lambda pair: (pair[1].get("round", 0), pair[0]))
  counted = []
  for _, match in ordered:
    result = season.record_match(match)
    if result is not None:
      counted.append(result)
  return counted
