"""A delivery plan: one route per vehicle, the routes in use first."""

from .model import RouteStats


class Route:
    """The stops one vehicle serves, in order, starting and ending at the depot."""

    def __init__(self, vehicle, stops=()):
        self.vehicle = vehicle
        self.stops = list(stops)

    def __len__(self):
        return len(self.stops)

    def __repr__(self):
        return f"Route({self.vehicle.id}, {len(self.stops)} stops)"


def route_stats(inst, vehicle, stops):
    """Load, distance, duration and cost of serving `stops` in order with `vehicle`."""
    dist, time = inst.dist, inst.time
    ready, service, demand = inst.ready, inst.service, inst.demand
    load = 0
    km = 0.0
    t = 0.0
    prev = 0
    for c in stops:
        load += demand[c]
        km += dist[prev, c]
        t += time[prev, c]
        if t < ready[c]:
            t = ready[c]
        t += service[c]
        prev = c
    if stops:
        km += dist[prev, 0]
        t += time[prev, 0]
        cost = km * vehicle.cost_per_km + vehicle.fixed_cost
    else:
        cost = 0.0
    return RouteStats(vehicle.id, len(stops), load, vehicle.capacity, round(km, 3), round(t, 1),
                      round(cost, 2))


def schedule_ok(inst, vehicle, stops):
    """Whether `stops` can be served in this order within their windows and the vehicle's shift."""
    time, ready, due, service = inst.time, inst.ready, inst.due, inst.service
    t = 0.0
    prev = 0
    for c in stops:
        t += time[prev, c]
        if t > due[c]:
            return False
        if t < ready[c]:
            t = ready[c]
        t += service[c]
        prev = c
    return t + time[prev, 0] <= vehicle.shift_end


class Plan:
    """Routes for every vehicle of the fleet.

    `routes[:n_active]` are the routes in use, which are never empty; the others are the idle
    vehicles' empty routes. `stats[r]` holds the totals of `routes[r]`, kept up to date by
    `refresh` so that scans and costing don't recompute them.
    """

    def __init__(self, inst, routes, stats=None, n_active=None):
        self.inst = inst
        self.routes = routes
        if n_active is None:
            self.routes.sort(key=lambda r: not r.stops)
            n_active = sum(1 for r in routes if r.stops)
        self.n_active = n_active
        if stats is None:
            stats = [route_stats(inst, r.vehicle, r.stops) for r in routes]
        self.stats = stats
        self.route_of = []
        self.pos_of = []

    @classmethod
    def from_sequences(cls, inst, sequences):
        """Assigns stop sequences to vehicles, the heaviest sequences to the largest vehicles."""
        fleet = sorted(inst.fleet, key=lambda v: (-v.capacity, v.cost_per_km, v.id))
        seqs = sorted(sequences, key=lambda s: -sum(inst.demand[c] for c in s))
        if len(seqs) > len(fleet):
            raise ValueError(f"{len(seqs)} routes needed but only {len(fleet)} vehicles")
        routes = []
        for k, v in enumerate(fleet):
            routes.append(Route(v, seqs[k] if k < len(seqs) else ()))
        return cls(inst, routes)

    def __repr__(self):
        return f"Plan({self.inst.name}, {self.n_active} routes)"

    def copy(self):
        routes = [Route(r.vehicle, r.stops) for r in self.routes]
        return Plan(self.inst, routes, list(self.stats), self.n_active)

    def cost(self):
        return sum(self.stats[r].cost for r in range(self.n_active))

    def distance(self):
        return sum(self.stats[r].distance for r in range(self.n_active))

    def refresh(self, r):
        """Recomputes the totals of route `r` after its stops changed, and returns them."""
        route = self.routes[r]
        self.stats[r] = route_stats(self.inst, route.vehicle, route.stops)
        return self.stats[r]

    def release(self, r):
        """Takes the emptied route `r` out of service, keeping the other routes in order."""
        route = self.routes.pop(r)
        stats = self.stats.pop(r)
        self.routes.append(route)
        self.stats.append(stats)
        self.n_active -= 1

    def open_route(self, demand):
        """Puts the cheapest idle vehicle able to carry `demand` into service; returns its index."""
        best = None
        for r in range(self.n_active, len(self.routes)):
            v = self.routes[r].vehicle
            if v.capacity >= demand and (best is None or
                                         (v.fixed_cost, v.cost_per_km) <
                                         (self.routes[best].vehicle.fixed_cost,
                                          self.routes[best].vehicle.cost_per_km)):
                best = r
        if best is None:
            return None
        k = self.n_active
        self.routes[k], self.routes[best] = self.routes[best], self.routes[k]
        self.stats[k], self.stats[best] = self.stats[best], self.stats[k]
        self.n_active += 1
        return k

    def index(self):
        """Records the route index and position of every stop in service (-1 for the depot)
        in `route_of` and `pos_of`."""
        route_of = [-1] * self.inst.n
        pos_of = [-1] * self.inst.n
        for r in range(self.n_active):
            for k, c in enumerate(self.routes[r].stops):
                route_of[c] = r
                pos_of[c] = k
        self.route_of = route_of
        self.pos_of = pos_of
