"""Improving a plan: descent over the neighbourhoods, restarted from ruined and recreated plans."""

import logging
import random

from .apply import apply_move
from .model import Move
from .moves import EPS, Neighbourhoods
from .plan import schedule_ok

log = logging.getLogger(__name__)

#: Order in which neighbourhoods are tried; the first one with an improving move wins.
SCANS = ("best_relocate", "best_swap", "best_segment", "best_tails", "best_two_opt")


def descend(plan, max_moves=100_000):
    """Applies improving moves until no neighbourhood has one; returns the number applied."""
    hoods = Neighbourhoods(plan)
    applied = 0
    while applied < max_moves:
        hoods.locate()
        for scan in SCANS:
            mv = getattr(hoods, scan)()
            if mv is not None:
                break
        else:
            break
        apply_move(plan, mv)
        applied += 1
    return applied


def ruin(plan, rng, share):
    """Removes the stops around a random centre from the plan; returns them, nearest first."""
    inst = plan.inst
    plan.index()
    route_of = plan.route_of
    centre = rng.randrange(1, inst.n)
    count = max(2, int(share * (inst.n - 1)))
    around = sorted(range(1, inst.n), key=lambda c: inst.dist[centre, c])[:count]
    removed = set(around)
    touched = sorted({route_of[c] for c in around}, reverse=True)
    for r in touched:
        stops = plan.routes[r].stops
        stops[:] = [c for c in stops if c not in removed]
        plan.refresh(r)
    for r in touched:
        if not plan.routes[r].stops:
            plan.release(r)
    return around


def recreate(plan, stops, rng):
    """Inserts `stops` again, each at its cheapest feasible place, opening routes if needed."""
    inst = plan.inst
    D = inst.dist
    order = list(stops)
    rng.shuffle(order)
    order.sort(key=lambda c: -inst.demand[c])
    for c in order:
        plan.index()
        route_of, pos_of = plan.route_of, plan.pos_of
        options = []
        for m in inst.near[c]:
            r = route_of[m]
            if r < 0:
                continue
            route = plan.routes[r]
            v = route.vehicle
            if plan.stats[r].load_kg + inst.demand[c] > v.capacity:
                continue
            s = route.stops
            k = pos_of[m]
            for j in (k, k + 1):
                a = s[j - 1] if j else 0
                b = s[j] if j < len(s) else 0
                extra = (D[a, c] + D[c, b] - D[a, b]) * v.cost_per_km
                options.append((extra, r, j))
        options.sort()
        for extra, r, j in options:
            s = plan.routes[r].stops
            if schedule_ok(inst, plan.routes[r].vehicle, s[:j] + [c] + s[j:]):
                s.insert(j, c)
                plan.refresh(r)
                break
        else:
            r = plan.open_route(inst.demand[c])
            if r is None:
                raise RuntimeError(f"no vehicle left for stop {inst.stop_id(c)}")
            plan.routes[r].stops.append(c)
            plan.refresh(r)


def improve(plan, rounds, seed, share=0.04):
    """Iterated local search: returns the cheapest plan found."""
    rng = random.Random(seed)
    applied = descend(plan)
    best = plan
    log.info("descent: %d moves, %d routes, cost %.2f", applied, best.n_active, best.cost())
    for k in range(1, rounds + 1):
        trial = best.copy()
        removed = ruin(trial, rng, share)
        recreate(trial, removed, rng)
        applied = descend(trial)
        if trial.cost() < best.cost() - EPS:
            best = trial
        log.info("round %d/%d: %d moves, trial cost %.2f, best %.2f (%d routes)", k, rounds,
                 applied, trial.cost(), best.cost(), best.n_active)
    best, removed = reduce_fleet(best, attempts=max(3, best.n_active // 8))
    log.info("fleet reduction: %d routes taken out, %d routes, cost %.2f", removed,
             best.n_active, best.cost())
    return best


def cheapest_insertion(plan, c, exclude):
    """The cheapest feasible place for stop `c` in a route other than `exclude`, as a move."""
    inst = plan.inst
    D = inst.dist
    best = None
    for r in range(plan.n_active):
        if r == exclude:
            continue
        route = plan.routes[r]
        v = route.vehicle
        if plan.stats[r].load_kg + inst.demand[c] > v.capacity:
            continue
        s = route.stops
        for j in range(len(s) + 1):
            a = s[j - 1] if j else 0
            b = s[j] if j < len(s) else 0
            extra = (D[a, c] + D[c, b] - D[a, b]) * v.cost_per_km
            if best is not None and extra >= best[0]:
                continue
            if schedule_ok(inst, v, s[:j] + [c] + s[j:]):
                best = (extra, r, j)
    return best


def reduce_fleet(plan, attempts):
    """Tries to take the lightest routes out of service by spreading their stops over the others.

    A route is given up only if all its stops find a place and the plan gets cheaper.
    """
    inst = plan.inst
    candidates = sorted(range(plan.n_active), key=lambda r: (plan.stats[r].load_kg, r))[:attempts]
    vehicles = [plan.routes[r].vehicle.id for r in candidates]
    saved = 0
    for vid in vehicles:
        trial = plan.copy()
        r = next(k for k in range(trial.n_active) if trial.routes[k].vehicle.id == vid)
        route = trial.routes[r]
        v1 = route.vehicle
        while route.stops:
            i = len(route.stops) - 1
            c = route.stops[i]
            place = cheapest_insertion(trial, c, r)
            if place is None:
                break
            extra, r2, j = place
            mv = Move("relocate", r, r2, i, j, 1, False, -round(extra, 4), v1.id,
                      trial.routes[r2].vehicle.id, inst.stop_id(c))
            apply_move(trial, mv)
        else:
            if trial.cost() < plan.cost() - EPS:
                plan = trial
                saved += 1
                log.info("fleet: %s taken out of service, cost %.2f", vid, plan.cost())
    return plan, saved
