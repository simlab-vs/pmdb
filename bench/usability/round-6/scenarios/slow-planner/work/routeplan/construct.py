"""Initial routes by the savings method of Clarke and Wright, with capacity and time windows."""

import logging

from .plan import Plan, schedule_ok

log = logging.getLogger(__name__)


def savings_routes(inst, capacity, shift_end, neighbours=None):
    """Builds stop sequences by merging routes along the largest savings first.

    Every stop starts on a route of its own. Two routes are merged end to start when the
    pair of stops joined is among each other's nearest neighbours, the merged route weighs at
    most `capacity` and it can be driven within the time windows and `shift_end`.
    """
    D = inst.dist
    near = inst.near if neighbours is None else [row[:neighbours] for row in inst.near]
    pairs = []
    for a in range(1, inst.n):
        da = D[0, a]
        for b in near[a]:
            s = da + D[0, b] - D[a, b]
            if s > 0:
                pairs.append((s, a, b))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
    log.info("savings: %d candidate joins", len(pairs))

    route_of = list(range(inst.n))
    seqs = {c: [c] for c in range(1, inst.n)}
    loads = {c: inst.demand[c] for c in range(1, inst.n)}
    probe = _Probe(shift_end)
    for s, a, b in pairs:
        ra, rb = route_of[a], route_of[b]
        if ra == rb:
            continue
        sa, sb = seqs[ra], seqs[rb]
        if sa[-1] != a or sb[0] != b:
            continue
        if loads[ra] + loads[rb] > capacity:
            continue
        merged = sa + sb
        if not schedule_ok(inst, probe, merged):
            continue
        seqs[ra] = merged
        loads[ra] += loads[rb]
        del seqs[rb], loads[rb]
        for c in sb:
            route_of[c] = ra
    return list(seqs.values())


class _Probe:
    """Stands in for a vehicle when only the shift end matters."""

    def __init__(self, shift_end):
        self.shift_end = shift_end


def initial_plan(inst):
    """Savings routes sized for the smallest vehicles, assigned largest loads first."""
    capacity = min(v.capacity for v in inst.fleet)
    shift_end = min(v.shift_end for v in inst.fleet)
    seqs = savings_routes(inst, capacity, shift_end)
    plan = Plan.from_sequences(inst, seqs)
    log.info("initial plan: %d routes, %.1f km, cost %.2f", plan.n_active, plan.distance(),
             plan.cost())
    return plan
