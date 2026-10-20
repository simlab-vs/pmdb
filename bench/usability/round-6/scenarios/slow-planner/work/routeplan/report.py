"""Checking the final plan and writing it out for dispatch."""

import os

from .plan import route_stats


def clock(minutes):
    """Minutes after 07:00 as a time of day."""
    m = int(round(minutes)) + 7 * 60
    return f"{m // 60:02d}:{m % 60:02d}"


def check_plan(inst, plan):
    """Recomputes every route from scratch; returns its totals and the problems found."""
    problems = []
    rows = []
    seen = [0] * inst.n
    for r in range(plan.n_active):
        route = plan.routes[r]
        v = route.vehicle
        st = route_stats(inst, v, route.stops)
        rows.append(st)
        if st.load_kg > v.capacity:
            problems.append(f"capacity: {v.id} carries {st.load_kg} kg, capacity {v.capacity} kg")
        t = 0.0
        prev = 0
        for c in route.stops:
            seen[c] += 1
            t += inst.time[prev, c]
            if t > inst.due[c]:
                problems.append(f"time window: {v.id} reaches {inst.stop_id(c)} at {clock(t)}, "
                                f"window closes {clock(inst.due[c])}")
            t = max(t, inst.ready[c]) + inst.service[c]
            prev = c
        t += inst.time[prev, 0]
        if t > v.shift_end:
            problems.append(f"shift: {v.id} back at {clock(t)}, shift ends {clock(v.shift_end)}")
    for c in range(1, inst.n):
        if seen[c] != 1:
            problems.append(f"stop {inst.stop_id(c)} served {seen[c]} times")
    return rows, problems


def write_outputs(inst, plan, rows, problems, out_dir):
    """Writes the dispatch sheet and the summary; returns the summary's text."""
    os.makedirs(out_dir, exist_ok=True)
    lines = []
    for r, st in zip(range(plan.n_active), rows):
        route = plan.routes[r]
        ids = " ".join(inst.stop_id(c) for c in route.stops)
        lines.append(f"{st.vehicle}\t{route.vehicle.kind}\t{st.stops} stops\t"
                     f"{st.load_kg}/{st.capacity} kg\t{st.distance:.1f} km\t"
                     f"back {clock(st.duration)}\t{ids}")
    with open(os.path.join(out_dir, f"routes_{inst.name}.tsv"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    km = sum(st.distance for st in rows)
    cost = sum(st.cost for st in rows)
    kinds = {}
    for r in range(plan.n_active):
        kind = plan.routes[r].vehicle.kind
        kinds[kind] = kinds.get(kind, 0) + 1
    used = ", ".join(f"{n} {k}s" for k, n in sorted(kinds.items()))
    summary = [
        f"plan for {inst.name}",
        f"stops: {inst.n - 1}",
        f"vehicles used: {plan.n_active} ({used})",
        f"distance: {km:.1f} km",
        f"cost: {cost:.2f}",
        f"utilisation: {sum(st.load_kg for st in rows) / sum(st.capacity for st in rows):.1%}",
        f"problems: {len(problems)}",
    ]
    summary += [f"  {p}" for p in problems]
    text = "\n".join(summary) + "\n"
    with open(os.path.join(out_dir, f"summary_{inst.name}.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return text
