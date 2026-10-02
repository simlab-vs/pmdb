"""A road network: intersections connected by streets with travel times in seconds."""


class Network:

  def __init__(self):
    # Maps each intersection to a list of `(neighbor, seconds, street)` triples.
    self.edges = {}
    self.positions = {}

  def add_intersection(self, name, x, y):
    self.edges.setdefault(name, [])
    self.positions[name] = (x, y)

  def add_street(self, street, a, b, seconds, one_way=False):
    self.edges[a].append((b, seconds, street))
    if not one_way:
      self.edges[b].append((a, seconds, street))

  def neighbors(self, name):
    return self.edges[name]


def heading(network, a, b):
  """Returns the compass heading from `a` to `b` as one of "N", "E", "S", "W"."""
  (ax, ay), (bx, by) = network.positions[a], network.positions[b]
  dx, dy = bx - ax, by - ay
  if abs(dx) >= abs(dy):
    return "E" if dx > 0 else "W"
  return "N" if dy > 0 else "S"


def turn_penalty(previous_heading, next_heading):
  """Returns the extra seconds needed to turn from `previous_heading` to `next_heading`."""
  if previous_heading is None or previous_heading == next_heading:
    return 0
  order = "NESW"
  delta = (order.index(next_heading) - order.index(previous_heading)) % 4
  if delta == 1:
    return 10  # right turn
  if delta == 3:
    return 25  # left turn
  return 60  # u-turn


def load(data):
  """Returns the network described by `data`."""
  network = Network()
  for name, (x, y) in sorted(data["intersections"].items()):
    network.add_intersection(name, x, y)
  for s in data["streets"]:
    network.add_street(s["name"], s["from"], s["to"], s["seconds"], s.get("one_way", False))
  return network
