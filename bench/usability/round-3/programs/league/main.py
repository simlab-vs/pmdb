"""Computes the final tables, playoffs and ratings of a league season stored in a JSON file."""

import json
import sys

from playoffs import ScoreFeed, run_playoff
from ratings import Ratings, rate_results
from season import Season, division_summary, merge_rules, play_season
from standings import TiebreakLog, longest_streak, standings, table_row


def final_tables(season, log):
  """Returns the table of every division, in division order."""
  tables = {}
  for division in season.divisions:
    name = division["name"]
    tables[name] = standings(season.teams_in(name), season.results_in(name), season.rules, log)
  return tables


def movements(season, tables, playoff_winners):
  """Returns the teams promoted and relegated between adjacent divisions."""
  promoted = []
  relegated = []
  last = len(season.divisions) - 1
  for i, division in enumerate(season.divisions):
    table = [record.name for record in tables[division["name"]]]
    if i > 0:
      count = division.get("promote", 0)
      promoted.extend(table[:count])
      winner = playoff_winners.get(division["name"])
      if winner is not None:
        promoted.append(winner)
    if i < last:
      count = division.get("relegate", 0)
      if count > 0:
        relegated.extend(table[-count:])
  return promoted, relegated


def play_playoffs(season, tables, ratings, scores):
  """Runs the playoff of every division below the top one that has one."""
  feed = ScoreFeed(scores)
  winners = {}
  lines = []
  for i, division in enumerate(season.divisions):
    size = division.get("playoff", 0)
    if i == 0 or size < 2:
      continue
    table = tables[division["name"]]
    winner, rounds = run_playoff(table, division.get("promote", 0), size, feed, ratings, season.rules)
    if winner is None:
      lines.append(f"playoff {division['name']}: not held")
      continue
    winners[division["name"]] = winner
    for text in rounds:
      lines.append(f"playoff {division['name']}: {text}")
  return winners, lines, feed


def summary_line(season, name):
  """Describes how the matches of a division went: results by venue and goals per match."""
  summary = division_summary(season.results_in(name))
  matches = summary["matches"]
  if matches == 0:
    return f"{name}: no matches"
  percent = lambda count: 100.0 * count / matches
  return (f"{name}: {matches} matches, home {percent(summary['home']):.0f}% draw "
          f"{percent(summary['draw']):.0f}% away {percent(summary['away']):.0f}%, "
          f"{summary['goals'] / matches:.2f} goals per match")


def venue_leaders(season):
  """Returns the teams with the most points at home and away, ties going to the better average."""
  records = sorted(season.records.values(), key=lambda r: r.name)
  home = max(records, key=lambda r: (r.home_points, r.points_per_game()))
  away = max(records, key=lambda r: (r.away_points, r.points_per_game()))
  sheets = max(records, key=lambda r: r.clean_sheets)
  return home, away, sheets


def best_fair_play(season):
  records = sorted(season.records.values(), key=lambda r: (r.fair_play / max(r.played, 1), r.name))
  return records[0]


def best_run(season):
  """Returns the team with the longest winning run, and its length."""
  best = None
  length = 0
  for name in sorted(season.records):
    run = longest_streak(season.records[name].form, "W")
    if run > length:
      best, length = name, run
  return best, length


def rating_lines(ratings, largest):
  ranking = ratings.ranking()
  top = ", ".join(f"{team} {ratings.current[team]:.1f}" for team in ranking[:3])
  changes = sorted(ratings.current, key=lambda team: (-ratings.change(team), team))
  rise, fall = changes[0], changes[-1]
  lines = [f"ratings top: {top}; bottom: {ranking[-1]} {ratings.current[ranking[-1]]:.1f}",
           f"biggest rise {rise} {ratings.change(rise):+.1f}, biggest fall {fall} {ratings.change(fall):+.1f}"]
  if largest is not None:
    change, result = largest
    lines.append(f"largest swing {result.home} {result.hg}-{result.ag} {result.away} ({change:+.2f})")
  peak_team = max(sorted(ratings.peak), key=lambda team: ratings.peak[team])
  luck = sorted(ratings.current, key=lambda team: (-ratings.overperformance(team), team))
  lines.append(f"overperformed {luck[0]} {ratings.overperformance(luck[0]):+.2f}, "
               f"underperformed {luck[-1]} {ratings.overperformance(luck[-1]):+.2f}")
  lines.append(f"rated matches {ratings.matches}, upsets {ratings.upsets}, "
               f"average {ratings.average():.2f}, peak {peak_team} {ratings.peak[peak_team]:.1f}")
  return lines


def main(path):
  with open(path) as f:
    data = json.load(f)
  rules = merge_rules(data.get("rules"))
  season = Season(data["divisions"], rules)
  counted = play_season(season, data["matches"])
  season.apply_deductions(data.get("deductions", []))

  log = TiebreakLog()
  tables = final_tables(season, log)
  ratings = Ratings(list(season.records), data.get("ratings", {}), rules["k"], rules["home_advantage"])
  largest = rate_results(ratings, counted)
  winners, playoff_lines, feed = play_playoffs(season, tables, ratings, data.get("playoff_scores", []))

  for division in season.divisions:
    print(division["name"])
    for position, record in enumerate(tables[division["name"]], start=1):
      print(table_row(position, record))
  for line in playoff_lines:
    print(line)
  promoted, relegated = movements(season, tables, winners)
  print(f"promoted: {', '.join(promoted) or 'none'}; relegated: {', '.join(relegated) or 'none'}")
  print(f"tiebreaks: {log.summary() or 'none'}")
  goals = sum(r.hg + r.ag for r in counted)
  print(f"matches {len(counted)} counted, {season.skipped} skipped, {season.forfeits} forfeits, "
        f"{goals} goals, {feed.predicted} playoff results predicted")
  for division in season.divisions:
    print(summary_line(season, division["name"]))
  home, away, sheets = venue_leaders(season)
  print(f"best home {home.name} {home.home_points}, best away {away.name} {away.away_points}, "
        f"clean sheets {sheets.name} {sheets.clean_sheets}")
  fair = best_fair_play(season)
  team, run = best_run(season)
  print(f"fair play: {fair.name} {fair.fair_play}; longest winning run: {team or '-'} {run}")
  for line in rating_lines(ratings, largest):
    print(line)


if __name__ == "__main__":
  main(sys.argv[1])
