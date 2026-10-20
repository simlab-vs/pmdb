"""The promotion playoff: a knockout bracket seeded from the final table.

Seed 1 meets the lowest seed, seed 2 the next lowest, and so on. Every round but the final is
played over two legs, the lower seed at home first; the final is a single match at a neutral
venue. Scores come from the input in bracket order; when they run out, the higher-rated team is
taken to win 1-0.
"""

from ratings import actual_score


class ScoreFeed:
  """Hands out the recorded playoff scores in order."""

  def __init__(self, scores):
    self.scores = list(scores)
    self.used = 0
    self.predicted = 0

  def next_score(self, ratings, home, away):
    """Returns (home goals, away goals, penalties or None) for the next match."""
    if self.used < len(self.scores):
      entry = self.scores[self.used]
      self.used += 1
      penalties = (entry[2], entry[3]) if len(entry) >= 4 else None
      return entry[0], entry[1], penalties
    self.predicted += 1
    if ratings.predict_winner(home, away) == home:
      return 1, 0, None
    return 0, 1, None


def bracket_size(available, wanted):
  """Returns the largest power of two not above `wanted` or `available`, or 0 below two teams."""
  size = 1
  while size * 2 <= min(available, wanted):
    size *= 2
  return size if size >= 2 else 0


def seed_pairs(seeds):
  """Pairs the first seed with the last, the second with the one before last, and so on."""
  pairs = []
  for i in range(len(seeds) // 2):
    pairs.append((seeds[i], seeds[len(seeds) - 1 - i]))
  return pairs


def decide_level_tie(higher, lower, penalties, note):
  """Returns the winner of a tie level after normal time, by penalties or else the higher seed."""
  if penalties is not None and penalties[0] != penalties[1]:
    note.append("pens")
    return higher if penalties[0] > penalties[1] else lower
  note.append("seed")
  return higher


def two_legged_tie(higher, lower, feed, ratings, rules):
  """Plays a two-legged tie; returns the winner and a description of the tie."""
  h1, a1, _ = feed.next_score(ratings, lower, higher)
  ratings.update(lower, higher, h1, a1)
  h2, a2, penalties = feed.next_score(ratings, higher, lower)
  ratings.update(higher, lower, h2, a2)
  higher_total = a1 + h2
  lower_total = h1 + a2
  note = []
  if higher_total > lower_total:
    winner = higher
  elif lower_total > higher_total:
    winner = lower
  elif rules["away_goals"] and a1 != a2:
    note.append("away goals")
    winner = higher if a1 > a2 else lower
  else:
    winner = decide_level_tie(higher, lower, penalties, note)
  text = f"{higher} {higher_total}-{lower_total} {lower}"
  if note:
    text += f" ({note[0]})"
  return winner, text


def final_match(higher, lower, feed, ratings):
  """Plays the single-match final at a neutral venue; returns the winner and a description."""
  hg, ag, penalties = feed.next_score(ratings, higher, lower)
  ratings.update(higher, lower, hg, ag, neutral=True)
  note = []
  outcome = actual_score(hg, ag)
  if outcome == 1.0:
    winner = higher
  elif outcome == 0.0:
    winner = lower
  else:
    winner = decide_level_tie(higher, lower, penalties, note)
  text = f"{higher} {hg}-{ag} {lower}"
  if note:
    text += f" ({note[0]})"
  return winner, text


def run_playoff(table, promote, wanted, feed, ratings, rules):
  """Runs the playoff among the teams placed just below the automatic promotion places.

  Returns the winner (or None when there are too few teams) and the descriptions of the rounds.
  """
  candidates = [record.name for record in table[promote:]]
  size = bracket_size(len(candidates), wanted)
  if size == 0:
    return None, []
  seeds = candidates[:size]
  position = {team: i for i, team in enumerate(seeds)}
  lines = []
  while len(seeds) > 2:
    winners = []
    ties = []
    for higher, lower in seed_pairs(seeds):
      winner, text = two_legged_tie(higher, lower, feed, ratings, rules)
      winners.append(winner)
      ties.append(text)
    lines.append("; ".join(ties))
    seeds = sorted(winners, key=lambda team: position[team])
  winner, text = final_match(seeds[0], seeds[1], feed, ratings)
  lines.append("final " + text)
  return winner, lines
