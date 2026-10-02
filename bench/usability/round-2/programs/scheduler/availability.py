"""Computes when rooms are free, within working hours."""

from bisect import bisect_right

from calendar_model import MINUTES_PER_DAY, expand, merge

# Working hours, in minutes since midnight.
OPENING = 8 * 60
CLOSING = 18 * 60


def busy_intervals(bookings):
  """Returns the merged busy intervals of a room given its bookings."""
  intervals = []
  for b in bookings:
    intervals.extend(expand(b))
  return merge(intervals)


def working_windows(days):
  """Returns the working-hours windows of the first `days` days of the week."""
  return [(d * MINUTES_PER_DAY + OPENING, d * MINUTES_PER_DAY + CLOSING) for d in range(days)]


def subtract(window, busy):
  """Returns the parts of `window` not covered by `busy`, which is sorted and disjoint."""
  start, end = window
  free = []
  i = bisect_right(busy, (start, start))
  if i > 0 and busy[i - 1][1] > start:
    i -= 1
  cursor = start
  while i < len(busy) and busy[i][0] < end:
    b_start, b_end = busy[i]
    if b_start > cursor:
      free.append((cursor, b_start))
    cursor = max(cursor, b_end)
    i += 1
  if cursor < end:
    free.append((cursor, end))
  return free


def free_slots(bookings, minimum, days=5):
  """Returns the free slots of a room lasting at least `minimum` minutes during working hours."""
  busy = busy_intervals(bookings)
  slots = []
  for window in working_windows(days):
    for slot in subtract(window, busy):
      if slot[1] - slot[0] >= minimum:
        slots.append(slot)
  return slots


def first_common_slot(rooms, minimum, days=5):
  """Returns the earliest slot of `minimum` minutes in which some room is free, as `(room, start)`."""
  best = None
  for name in sorted(rooms):
    for start, end in free_slots(rooms[name], minimum, days):
      if best is None or start < best[1]:
        best = (name, start)
      break
  return best


def utilization(bookings, days=5):
  """Returns the percentage of working time during which the room is busy, rounded down."""
  busy = busy_intervals(bookings)
  total = 0
  covered = 0
  for window in working_windows(days):
    total += window[1] - window[0]
    for b_start, b_end in busy:
      overlap = min(b_end, window[1]) - max(b_start, window[0])
      if overlap > 0:
        covered += overlap
  return covered * 100 // total
