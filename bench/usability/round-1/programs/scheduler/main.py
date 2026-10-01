"""Prints a weekly availability report for the rooms described in a JSON file."""

import json
import sys

from availability import first_common_slot, free_slots, utilization
from calendar_model import conflicts, expand, format_time


def report(rooms, minimum):
  for name in sorted(rooms):
    bookings = rooms[name]
    occurrences = [o for b in bookings for o in expand(b)]
    print(f"room {name}: {len(occurrences)} occurrences, {utilization(bookings)}% busy")
    for i, j in conflicts(occurrences):
      print(f"  conflict: {format_time(occurrences[i][0])} and {format_time(occurrences[j][0])}")
    for start, end in free_slots(bookings, minimum):
      print(f"  free {format_time(start)} - {format_time(end)}")
  best = first_common_slot(rooms, minimum)
  if best is None:
    print(f"no room is free for {minimum} minutes")
  else:
    print(f"first free: room {best[0]} at {format_time(best[1])}")


def main(path):
  with open(path) as f:
    data = json.load(f)
  report(data["rooms"], data["minimum"])


if __name__ == "__main__":
  main(sys.argv[1])
