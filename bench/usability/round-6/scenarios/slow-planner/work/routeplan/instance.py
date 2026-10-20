"""Loading a planning day: depot, stops and fleet, and the travel matrices between them."""

import json
import logging
import math
from array import array

from .model import Stop, Vehicle

log = logging.getLogger(__name__)

#: Average speed in town, in km per minute (about 33 km/h).
SPEED_KM_PER_MIN = 0.55
#: Minutes lost per leg to parking and walking to the door.
LEG_OVERHEAD_MIN = 1.5
#: Detour factor from straight-line to road distance.
ROAD_FACTOR = 1.28


class Instance:
    """Everything that stays fixed while planning a day.

    Nodes are numbered from 0 (the depot) to n - 1. `dist[a, b]` is the road distance in km and
    `time[a, b]` the driving time in minutes from node `a` to node `b`.
    """

    def __init__(self, name, depot, stops, fleet, neighbours=24):
        nodes = [depot] + list(stops)
        self.dist, self.time = travel_matrices(nodes)
        self.name = name
        self.nodes = nodes
        self.n = len(nodes)
        self.fleet = list(fleet)
        self.demand = [s.demand for s in nodes]
        self.ready = [s.ready for s in nodes]
        self.due = [s.due for s in nodes]
        self.service = [s.service for s in nodes]
        self.near = nearest_neighbours(self.dist, self.n, neighbours)

    def __repr__(self):
        return f"Instance({self.name!r}, {self.n - 1} stops, {len(self.fleet)} vehicles)"

    def stop_id(self, node):
        return self.nodes[node].id


def travel_matrices(nodes):
    """Road distances and driving times between all pairs of nodes, as n x n matrices."""
    n = len(nodes)
    dist = array("d", bytes(8 * n * n))
    time = array("d", bytes(8 * n * n))
    xs = [s.x for s in nodes]
    ys = [s.y for s in nodes]
    for a in range(n):
        xa, ya = xs[a], ys[a]
        row = a * n
        for b in range(a + 1, n):
            d = math.hypot(xs[b] - xa, ys[b] - ya) * ROAD_FACTOR
            t = d / SPEED_KM_PER_MIN + LEG_OVERHEAD_MIN
            dist[row + b] = d
            dist[b * n + a] = d
            time[row + b] = t
            time[b * n + a] = t
    shape = (n, n)
    return (memoryview(dist).cast("B").cast("d", shape),
            memoryview(time).cast("B").cast("d", shape))


def nearest_neighbours(dist, n, k):
    """For each stop, the `k` closest other stops (never the depot), closest first."""
    near = [[] for _ in range(n)]
    for a in range(1, n):
        row = sorted(range(1, n), key=lambda b: dist[a, b])
        near[a] = [b for b in row[:k + 1] if b != a][:k]
    return near


def load_day(path, fleet_path, neighbours=24):
    """Reads a day's orders and the fleet available that day."""
    with open(path, encoding="utf-8") as f:
        day = json.load(f)
    with open(fleet_path, encoding="utf-8") as f:
        fleet_doc = json.load(f)
    depot = _stop(day["depot"], default_window=(0, day["horizon"]))
    stops = [_stop(o, default_window=(0, day["horizon"])) for o in day["orders"]]
    unavailable = set(day.get("unavailable_vehicles", []))
    fleet = []
    for v in fleet_doc["vehicles"]:
        if v["id"] in unavailable:
            continue
        kind = fleet_doc["kinds"][v["kind"]]
        fleet.append(Vehicle(v["id"], v["kind"], kind["capacity"], kind["cost_per_km"],
                             kind["fixed_cost"], v.get("shift_end", day["horizon"])))
    log.info("loaded %s: %d stops, %d vehicles available", day["date"], len(stops), len(fleet))
    total = sum(s.demand for s in stops)
    capacity = sum(v.capacity for v in fleet)
    if total > capacity:
        raise ValueError(f"orders total {total} kg but the fleet carries only {capacity} kg")
    inst = Instance(day["date"], depot, stops, fleet, neighbours)
    log.info("travel matrices ready (%d x %d)", inst.n, inst.n)
    return inst


def _stop(doc, default_window):
    ready, due = doc.get("window", default_window)
    return Stop(doc["id"], float(doc["x"]), float(doc["y"]), int(doc.get("kg", 0)),
                int(ready), int(due), int(doc.get("service", 0)))
