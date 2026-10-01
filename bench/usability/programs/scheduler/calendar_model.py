"""Bookings of meeting rooms, expressed in minutes since the start of the week (Monday 00:00).

A booking is a half-open interval `[start, end)`. Recurring bookings repeat every `period` days.
"""

MINUTES_PER_DAY = 24 * 60
MINUTES_PER_WEEK = 7 * MINUTES_PER_DAY


def parse_time(text):
  """Parses `"<day> HH:MM"` (e.g. `"tue 09:30"`) into minutes since the start of the week."""
  days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
  day, clock = text.split()
  hours, minutes = clock.split(":")
  return days.index(day) * MINUTES_PER_DAY + int(hours) * 60 + int(minutes)


def format_time(minute):
  days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
  day, rest = divmod(minute, MINUTES_PER_DAY)
  return f"{days[day]} {rest // 60:02d}:{rest % 60:02d}"


def expand(booking):
  """Returns the occurrences of `booking` within the week as `(start, end)` pairs.

  Occurrences that cross the end of the week are cut at the end of the week.
  """
  start = parse_time(booking["start"])
  end = start + booking["duration"]
  period = booking.get("every_days")
  occurrences = []
  while start < MINUTES_PER_WEEK:
    occurrences.append((start, min(end, MINUTES_PER_WEEK)))
    if period is None:
      break
    start += period * MINUTES_PER_DAY
    end += period * MINUTES_PER_DAY
  return occurrences


def merge(intervals):
  """Returns the union of `intervals` as a sorted list of disjoint intervals.

  Intervals that touch (one ends where the other starts) are merged.
  """
  merged = []
  for start, end in sorted(intervals):
    if merged and start <= merged[-1][1]:
      merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    else:
      merged.append((start, end))
  return merged


def conflicts(intervals):
  """Returns the pairs of indices of `intervals` that overlap, in increasing order."""
  order = sorted(range(len(intervals)), key=lambda i: intervals[i])
  pairs = []
  for a in range(len(order)):
    i = order[a]
    for b in range(a + 1, len(order)):
      j = order[b]
      if intervals[j][0] >= intervals[i][1]:
        break
      pairs.append((min(i, j), max(i, j)))
  return sorted(pairs)
