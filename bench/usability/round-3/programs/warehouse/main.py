"""Replays a period of warehouse events stored in a JSON file and prints the closing report."""

import json
import sys

from engine import Warehouse, run_events
from report import render


def load(path):
  """Returns the sites, items and events described in the file at `path`."""
  with open(path) as f:
    data = json.load(f)
  return data["sites"], data["items"], data["events"]


def main(path):
  sites, items, events = load(path)
  warehouse = Warehouse(sites, items)
  run_events(warehouse, events)
  for line in render(warehouse):
    print(line)


if __name__ == "__main__":
  main(sys.argv[1])
