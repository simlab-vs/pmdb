"""Neighbourhood scans: each finds the best improving move of one kind, or None.

Gains are in cost units (distance times the vehicle's cost per km, plus the fixed cost of a
vehicle taken out of service). A move is only returned if every route it changes stays within
its vehicle's capacity and every stop is reached within its time window.
"""

from .model import Move
from .plan import schedule_ok

EPS = 1e-6
SEGMENT_LENGTHS = (2, 3)


class Neighbourhoods:
    """Scans over the routes in service of a plan."""

    def __init__(self, plan):
        self.plan = plan
        self.route_of = []
        self.pos_of = []

    def __repr__(self):
        return f"Neighbourhoods({self.plan!r})"

    def locate(self):
        """Indexes the stops' current routes and positions; call after each change to the plan."""
        self.plan.index()
        self.route_of, self.pos_of = self.plan.route_of, self.plan.pos_of

    def best_relocate(self):
        """Moves one stop to another route, next to one of its nearest neighbours."""
        plan = self.plan
        inst = plan.inst
        D = inst.dist
        demand = inst.demand
        route_of, pos_of = self.route_of, self.pos_of
        best, best_gain = None, EPS
        for r1 in range(plan.n_active):
            route1 = plan.routes[r1]
            s1, v1 = route1.stops, route1.vehicle
            n1 = len(s1)
            for i, c in enumerate(s1):
                p = s1[i - 1] if i else 0
                q = s1[i + 1] if i + 1 < n1 else 0
                saved = (D[p, c] + D[c, q] - D[p, q]) * v1.cost_per_km
                if n1 == 1:
                    saved += v1.fixed_cost
                for m in inst.near[c]:
                    r2 = route_of[m]
                    if r2 < 0 or r2 == r1:
                        continue
                    route2 = plan.routes[r2]
                    v2 = route2.vehicle
                    if plan.stats[r2].load_kg + demand[c] > v2.capacity:
                        continue
                    s2 = route2.stops
                    k = pos_of[m]
                    for j in (k, k + 1):
                        a = s2[j - 1] if j else 0
                        b = s2[j] if j < len(s2) else 0
                        gain = saved - (D[a, c] + D[c, b] - D[a, b]) * v2.cost_per_km
                        if gain > best_gain and schedule_ok(inst, v2, s2[:j] + [c] + s2[j:]):
                            best_gain = gain
                            best = Move("relocate", r1, r2, i, j, 1, False, round(gain, 4),
                                        v1.id, v2.id, inst.stop_id(c))
        return best

    def best_swap(self):
        """Exchanges two stops of different routes that are near each other."""
        plan = self.plan
        inst = plan.inst
        D = inst.dist
        demand = inst.demand
        route_of, pos_of = self.route_of, self.pos_of
        best, best_gain = None, EPS
        for r1 in range(plan.n_active):
            route1 = plan.routes[r1]
            s1, v1 = route1.stops, route1.vehicle
            n1 = len(s1)
            load1 = plan.stats[r1].load_kg
            for i, c1 in enumerate(s1):
                p1 = s1[i - 1] if i else 0
                q1 = s1[i + 1] if i + 1 < n1 else 0
                out1 = D[p1, c1] + D[c1, q1]
                for m in inst.near[c1]:
                    r2 = route_of[m]
                    if r2 <= r1:
                        continue
                    route2 = plan.routes[r2]
                    v2 = route2.vehicle
                    if load1 - demand[c1] + demand[m] > v1.capacity:
                        continue
                    if plan.stats[r2].load_kg - demand[m] + demand[c1] > v2.capacity:
                        continue
                    s2 = route2.stops
                    j = pos_of[m]
                    p2 = s2[j - 1] if j else 0
                    q2 = s2[j + 1] if j + 1 < len(s2) else 0
                    gain = ((out1 - D[p1, m] - D[m, q1]) * v1.cost_per_km
                            + (D[p2, m] + D[m, q2] - D[p2, c1] - D[c1, q2]) * v2.cost_per_km)
                    if gain <= best_gain:
                        continue
                    new1 = s1[:i] + [m] + s1[i + 1:]
                    new2 = s2[:j] + [c1] + s2[j + 1:]
                    if schedule_ok(inst, v1, new1) and schedule_ok(inst, v2, new2):
                        best_gain = gain
                        best = Move("swap", r1, r2, i, j, 1, False, round(gain, 4),
                                    v1.id, v2.id, inst.stop_id(c1))
        return best

    def best_segment(self):
        """Moves two or three consecutive stops to another route, possibly reversed."""
        plan = self.plan
        inst = plan.inst
        D = inst.dist
        demand = inst.demand
        route_of, pos_of = self.route_of, self.pos_of
        best, best_gain = None, EPS
        for r1 in range(plan.n_active):
            route1 = plan.routes[r1]
            s1, v1 = route1.stops, route1.vehicle
            n1 = len(s1)
            for length in SEGMENT_LENGTHS:
                if length >= n1:
                    continue
                for i in range(n1 - length + 1):
                    seg = s1[i:i + length]
                    f, l = seg[0], seg[-1]
                    p = s1[i - 1] if i else 0
                    q = s1[i + length] if i + length < n1 else 0
                    inner = 0.0
                    seg_load = 0
                    for x, y in zip(seg, seg[1:]):
                        inner += D[x, y]
                    for x in seg:
                        seg_load += demand[x]
                    saved = (D[p, f] + inner + D[l, q] - D[p, q]) * v1.cost_per_km
                    seen = set()
                    for end in (f, l):
                        for m in inst.near[end]:
                            r2 = route_of[m]
                            if r2 < 0 or r2 == r1 or m in seen:
                                continue
                            seen.add(m)
                            route2 = plan.routes[r2]
                            v2 = route2.vehicle
                            if plan.stats[r2].load_kg + seg_load > v2.capacity:
                                continue
                            s2 = route2.stops
                            k = pos_of[m]
                            for j in (k, k + 1):
                                a = s2[j - 1] if j else 0
                                b = s2[j] if j < len(s2) else 0
                                base = inner - D[a, b]
                                for reverse in (False, True):
                                    x, y = (l, f) if reverse else (f, l)
                                    gain = saved - (D[a, x] + D[y, b] + base) * v2.cost_per_km
                                    if gain <= best_gain:
                                        continue
                                    moved = seg[::-1] if reverse else seg
                                    if schedule_ok(inst, v2, s2[:j] + moved + s2[j:]):
                                        best_gain = gain
                                        best = Move("segment", r1, r2, i, j, length, reverse,
                                                    round(gain, 4), v1.id, v2.id,
                                                    inst.stop_id(f))
        return best

    def best_tails(self):
        """Exchanges the ends of two routes (2-opt*), joining a stop to a neighbour's tail."""
        plan = self.plan
        inst = plan.inst
        D = inst.dist
        demand = inst.demand
        route_of, pos_of = self.route_of, self.pos_of
        prefix_km, prefix_kg, total_km = [], [], []
        for r in range(plan.n_active):
            s = plan.routes[r].stops
            km, kg = [0.0], [0]
            prev = 0
            for c in s:
                km.append(km[-1] + D[prev, c])
                kg.append(kg[-1] + demand[c])
                prev = c
            prefix_km.append(km)
            prefix_kg.append(kg)
            total_km.append(km[-1] + D[prev, 0])
        best, best_gain = None, EPS
        for r1 in range(plan.n_active):
            route1 = plan.routes[r1]
            s1, v1 = route1.stops, route1.vehicle
            n1 = len(s1)
            km1, kg1, t1 = prefix_km[r1], prefix_kg[r1], total_km[r1]
            for a in range(1, n1 + 1):
                x = s1[a - 1]
                for m in inst.near[x]:
                    r2 = route_of[m]
                    if r2 < 0 or r2 == r1:
                        continue
                    route2 = plan.routes[r2]
                    s2, v2 = route2.stops, route2.vehicle
                    n2 = len(s2)
                    b = pos_of[m]
                    if b == 0 and a == n1:
                        continue
                    km2, kg2, t2 = prefix_km[r2], prefix_kg[r2], total_km[r2]
                    load1 = kg1[a] + kg2[n2] - kg2[b]
                    load2 = kg2[b] + kg1[n1] - kg1[a]
                    if load1 > v1.capacity or load2 > v2.capacity:
                        continue
                    new_km1 = km1[a] + D[x, m] + t2 - km2[b + 1]
                    y = s2[b - 1] if b else 0
                    if a < n1:
                        new_km2 = km2[b] + D[y, s1[a]] + t1 - km1[a + 1]
                    else:
                        new_km2 = km2[b] + D[y, 0]
                    gain = ((t1 - new_km1) * v1.cost_per_km + (t2 - new_km2) * v2.cost_per_km)
                    if gain <= best_gain:
                        continue
                    new1 = s1[:a] + s2[b:]
                    new2 = s2[:b] + s1[a:]
                    if schedule_ok(inst, v1, new1) and schedule_ok(inst, v2, new2):
                        best_gain = gain
                        best = Move("tails", r1, r2, a, b, 0, False, round(gain, 4),
                                    v1.id, v2.id, inst.stop_id(x))
        return best

    def best_two_opt(self):
        """Reverses a stretch of a single route."""
        plan = self.plan
        inst = plan.inst
        D = inst.dist
        best, best_gain = None, EPS
        for r in range(plan.n_active):
            route = plan.routes[r]
            s, v = route.stops, route.vehicle
            n = len(s)
            for i in range(n - 1):
                p = s[i - 1] if i else 0
                ci = s[i]
                for j in range(i + 1, n):
                    cj = s[j]
                    q = s[j + 1] if j + 1 < n else 0
                    gain = (D[p, ci] + D[cj, q] - D[p, cj] - D[ci, q]) * v.cost_per_km
                    if gain > best_gain:
                        new = s[:i] + s[i:j + 1][::-1] + s[j + 1:]
                        if schedule_ok(inst, v, new):
                            best_gain = gain
                            best = Move("two_opt", r, r, i, j, j - i + 1, True, round(gain, 4),
                                        v.id, v.id, inst.stop_id(ci))
        return best
