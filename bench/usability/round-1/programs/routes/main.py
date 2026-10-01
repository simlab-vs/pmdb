"""Prints the fastest routes for the trips described in a JSON file."""

import json
import sys

from network import load
from planner import describe, fastest_route


def main(path):
  with open(path) as f:
    data = json.load(f)
  network = load(data)
  for source, target in data["trips"]:
    result = fastest_route(network, source, target)
    if result is None:
      print(f"{source} -> {target}: unreachable")
      continue
    seconds, steps = result
    print(f"{source} -> {target}: {seconds // 60}m{seconds % 60:02d}s via {', '.join(describe(steps))}")


if __name__ == "__main__":
  main(sys.argv[1])
