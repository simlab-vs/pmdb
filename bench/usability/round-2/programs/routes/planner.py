"""Finds fastest routes, taking turn penalties into account."""

import heapq

from network import heading, turn_penalty


def fastest_route(network, source, target):
  """Returns `(seconds, path)` for the fastest route from `source` to `target`, or `None`.

  The search state is an intersection together with the heading used to reach it, since the cost
  of the next street depends on the turn.
  """
  start = (source, None)
  best = {start: 0}
  previous = {}
  queue = [(0, source, None)]
  while queue:
    seconds, node, arrived = heapq.heappop(queue)
    if seconds > best.get((node, arrived), float("inf")):
      continue
    if node == target:
      return seconds, reconstruct(previous, (node, arrived))
    for neighbor, cost, street in network.neighbors(node):
      direction = heading(network, node, neighbor)
      total = seconds + cost + turn_penalty(arrived, direction)
      state = (neighbor, direction)
      if total < best.get(state, float("inf")):
        best[state] = total
        previous[state] = ((node, arrived), street)
        heapq.heappush(queue, (total, neighbor, direction))
  return None


def reconstruct(previous, state):
  """Returns the intersections and streets along the path ending at `state`."""
  steps = [state[0]]
  while state in previous:
    state, street = previous[state]
    steps.append(street)
    steps.append(state[0])
  steps.reverse()
  return steps


def describe(path):
  """Returns turn-by-turn directions for `path`, merging consecutive steps on the same street."""
  directions = []
  for i in range(1, len(path), 2):
    street = path[i]
    if directions and directions[-1][0] == street:
      directions[-1] = (street, directions[-1][1] + 1)
    else:
      directions.append((street, 1))
  return [f"{street} ({blocks} block{'s' if blocks > 1 else ''})" for street, blocks in directions]
