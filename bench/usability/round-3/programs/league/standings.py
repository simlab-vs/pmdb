"""League tables: ordering teams by points and the tiebreakers of the competition.

Teams level on points are separated first by a head-to-head mini-table of the matches between
them (points, then goal difference, then goals scored in those matches). When that splits the
group, every smaller group still level is separated again by its own mini-table. When it does
not, the overall goal difference, goals scored and fair-play points (fewer is better) decide, and
finally the team name.
"""

from season import match_points


class TiebreakLog:
  """Counts which criterion separated each pair of adjacent teams that were level on points."""

  CRITERIA = ("head-to-head", "goal difference", "goals scored", "fair play", "name")

  def __init__(self):
    self.counts = {criterion: 0 for criterion in self.CRITERIA}

  def note(self, criterion):
    self.counts[criterion] += 1

  def summary(self):
    return ", ".join(f"{c} {self.counts[c]}" for c in self.CRITERIA if self.counts[c] > 0)


def mini_table(names, results, rules):
  """Returns the (points, goal difference, goals) of each team in matches among `names`."""
  table = {name: [0, 0, 0] for name in names}
  for result in results:
    if result.home not in table or result.away not in table:
      continue
    home = table[result.home]
    away = table[result.away]
    home[0] += match_points(result.hg, result.ag, rules)
    away[0] += match_points(result.ag, result.hg, rules)
    home[1] += result.hg - result.ag
    away[1] += result.ag - result.hg
    home[2] += result.hg
    away[2] += result.ag
  return {name: tuple(values) for name, values in table.items()}


def overall_key(record):
  """Returns the sort key of the overall criteria, smallest first for the better team."""
  return (-record.goal_difference(), -record.goals_for, record.fair_play, record.name)


def separating_criterion(a, b):
  """Returns the first overall criterion on which records `a` and `b` differ."""
  if a.goal_difference() != b.goal_difference():
    return "goal difference"
  if a.goals_for != b.goals_for:
    return "goals scored"
  if a.fair_play != b.fair_play:
    return "fair play"
  return "name"


def partition(group, key):
  """Splits records sorted by `key` into runs that share the same key."""
  runs = []
  for record in group:
    if runs and key(runs[-1][0]) == key(record):
      runs[-1].append(record)
    else:
      runs.append([record])
  return runs


def rank_level_group(group, results, rules, log):
  """Orders records that are level on points, by the head-to-head and overall criteria."""
  if len(group) == 1:
    return list(group)
  names = [record.name for record in group]
  table = mini_table(names, results, rules)
  h2h = lambda record: tuple(-x for x in table[record.name])
  ordered = sorted(group, key=h2h)
  runs = partition(ordered, h2h)
  if len(runs) == 1:
    ordered = sorted(group, key=overall_key)
    for a, b in zip(ordered, ordered[1:]):
      log.note(separating_criterion(a, b))
    return ordered
  ranked = []
  for i, run in enumerate(runs):
    if i > 0:
      log.note("head-to-head")
    ranked.extend(rank_level_group(run, results, rules, log))
  return ranked


def standings(records, results, rules, log):
  """Returns the records of one division in table order."""
  by_points = sorted(records, key=lambda record: -record.total_points())
  table = []
  for group in partition(by_points, lambda record: record.total_points()):
    table.extend(rank_level_group(group, results, rules, log))
  return table


def table_row(position, record):
  """Formats one line of a league table."""
  return (f"{position:>2} {record.name:<12} {record.played:>2} {record.won:>2} {record.drawn:>2} "
          f"{record.lost:>2} {record.goals_for:>3}:{record.goals_against:<3} "
          f"{record.goal_difference():>+4} {record.total_points():>4}"
          + (f" (-{record.deducted})" if record.deducted else ""))


def longest_streak(form, outcome):
  """Returns the longest run of `outcome` ('W', 'D' or 'L') in a team's form."""
  best = 0
  current = 0
  for result in form:
    if result == outcome:
      current += 1
      best = max(best, current)
    else:
      current = 0
  return best
