"""Elo ratings of the teams, updated after every counted match.

The home side gets a rating bonus when the expected result is computed. Wins by a wider margin
move the ratings more. Forfeits are not rated, since no football was played.
"""

DEFAULT_RATING = 1500.0
SCALE = 400.0


def expected_score(rating, opponent):
  """Returns the expected score (between 0 and 1) of a team rated `rating` against `opponent`."""
  return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / SCALE))


def margin_multiplier(goal_difference):
  """Returns the factor applied to rating changes for a win by `goal_difference` goals."""
  margin = abs(goal_difference)
  if margin <= 1:
    return 1.0
  if margin == 2:
    return 1.5
  return (11.0 + margin) / 8.0


def actual_score(scored, conceded):
  if scored > conceded:
    return 1.0
  if scored == conceded:
    return 0.5
  return 0.0


class Ratings:
  """The current rating of every team and the history of its changes."""

  def __init__(self, teams, initial, k, home_advantage):
    self.k = k
    self.home_advantage = home_advantage
    self.start = {team: float(initial.get(team, DEFAULT_RATING)) for team in teams}
    self.current = dict(self.start)
    self.peak = dict(self.start)
    self.expected = {team: 0.0 for team in teams}
    self.earned = {team: 0.0 for team in teams}
    self.matches = 0
    self.upsets = 0

  def update(self, home, away, hg, ag, neutral=False):
    """Updates both ratings after a match and returns the change of the home team's rating."""
    advantage = 0 if neutral else self.home_advantage
    home_rating = self.current[home]
    away_rating = self.current[away]
    expected = expected_score(home_rating + advantage, away_rating)
    actual = actual_score(hg, ag)
    change = self.k * margin_multiplier(hg - ag) * (actual - expected)
    self.current[home] = home_rating + change
    self.current[away] = away_rating - change
    self.expected[home] += expected
    self.expected[away] += 1.0 - expected
    self.earned[home] += actual
    self.earned[away] += 1.0 - actual
    for team in (home, away):
      self.peak[team] = max(self.peak[team], self.current[team])
    self.matches += 1
    if (actual == 1.0 and expected < 0.3) or (actual == 0.0 and expected > 0.7):
      self.upsets += 1
    return change

  def predict_winner(self, first, second):
    """Returns the team with the higher rating, `first` when they are equal."""
    if self.current[second] > self.current[first]:
      return second
    return first

  def change(self, team):
    return self.current[team] - self.start[team]

  def overperformance(self, team):
    """Returns how many match scores more than expected `team` earned (a win scores 1)."""
    return self.earned[team] - self.expected[team]

  def ranking(self):
    """Returns the teams ordered by current rating, best first, then by name."""
    return sorted(self.current, key=lambda team: (-self.current[team], team))

  def average(self):
    teams = list(self.current)
    return sum(self.current[t] for t in teams) / len(teams) if teams else DEFAULT_RATING


def rate_results(ratings, results):
  """Applies the counted results in order, skipping forfeits; returns the largest swing."""
  largest = None
  for result in results:
    if result.is_forfeit():
      continue
    change = ratings.update(result.home, result.away, result.hg, result.ag)
    if largest is None or abs(change) > abs(largest[0]):
      largest = (change, result)
  return largest
