#!/usr/bin/env python3
"""Grades a fix of slow-planner: python3 oracle.py DIR [--full] [--make-expected].

DIR is the agent's final /work. The planner is run on hidden days (small enough to plan in
seconds; on 6 of the 8 the unfixed planner overloads a vehicle). For each, the routes it writes
are checked independently of the planner's own checks: every stop served once, capacities,
time windows and shifts, and a cost within 1% of the reference fix's. Then, if the planner's
internals still have the shape of the original (Plan.stats, Plan.refresh, search.apply_move),
the cached route totals are compared with totals recomputed from scratch after every move on
one hidden day, which a fix that only repairs the final plan doesn't pass.
--full also plans the original day (about 2-3 minutes). --make-expected writes
hidden/expected.json from the reference fix (fix.patch applied to work/).
"""
import concurrent.futures
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HIDDEN = os.path.join(HERE, "hidden")
PARAMS = ["--rounds", "8", "--neighbours", "24"]
TOLERANCE = 0.01


def days():
    out = []
    for d in sorted(glob.glob(os.path.join(HIDDEN, "d*"))):
        seed = os.path.basename(d).split("_")[1]
        out.append((os.path.basename(d), glob.glob(os.path.join(d, "orders_*.json"))[0],
                    os.path.join(d, "fleet.json"), PARAMS + ["--seed", seed]))
    return out


def run_planner(work, orders, fleet, params, timeout):
    out = tempfile.mkdtemp(prefix="sp-out-")
    try:
        p = subprocess.run([sys.executable, "plan_day.py", orders, "--fleet", fleet, "-o", out]
                           + params, cwd=work, capture_output=True, text=True, timeout=timeout)
        tsv = glob.glob(os.path.join(out, "routes_*.tsv"))
        routes = open(tsv[0]).read() if tsv else None
        return p.returncode, p.stdout, p.stderr[-2000:], routes
    except subprocess.TimeoutExpired:
        return None, "", "timeout", None
    finally:
        shutil.rmtree(out, ignore_errors=True)


def verify(orders_path, fleet_path, routes_text):
    """Independent check of a dispatch sheet; returns (problems, cost)."""
    day = json.load(open(orders_path))
    fdoc = json.load(open(fleet_path))
    horizon = day["horizon"]
    nodes = {o["id"]: o for o in day["orders"]}
    depot = day["depot"]
    kinds = fdoc["kinds"]
    vehicles = {v["id"]: v for v in fdoc["vehicles"]}

    def d(a, b):
        return math.hypot(b["x"] - a["x"], b["y"] - a["y"]) * 1.28

    problems, cost, seen = [], 0.0, {}
    for line in routes_text.strip().splitlines():
        cols = line.split("\t")
        vid, ids = cols[0], cols[-1].split()
        v = vehicles[vid]
        kind = kinds[v["kind"]]
        shift_end = v.get("shift_end", horizon)
        load, km, t, prev = 0, 0.0, 0.0, depot
        for sid in ids:
            seen[sid] = seen.get(sid, 0) + 1
            o = nodes[sid]
            load += int(o.get("kg", 0))
            leg = d(prev, o)
            km += leg
            t += leg / 0.55 + 1.5
            ready, due = o.get("window", (0, horizon))
            if t > due + 1e-6:
                problems.append(f"{vid} late at {sid}")
            t = max(t, ready) + o.get("service", 0)
            prev = o
        leg = d(prev, depot)
        km += leg
        t += leg / 0.55 + 1.5
        if t > shift_end + 1e-6:
            problems.append(f"{vid} back after its shift")
        if load > kind["capacity"]:
            problems.append(f"{vid} carries {load} kg > {kind['capacity']} kg")
        if ids:
            cost += km * kind["cost_per_km"] + kind["fixed_cost"]
    for sid in nodes:
        if seen.get(sid) != 1:
            problems.append(f"stop {sid} served {seen.get(sid, 0)} times")
    return problems, cost


INVARIANT = r'''
import sys, glob
sys.path.insert(0, ".")
from routeplan import search, plan as P
from routeplan.instance import load_day
from routeplan.construct import initial_plan
orig = search.apply_move
bad = []
def checked(plan, mv):
    res = orig(plan, mv)
    for r in range(plan.n_active):
        route = plan.routes[r]
        fresh = P.route_stats(plan.inst, route.vehicle, route.stops)
        if plan.stats[r] != fresh and not bad:
            bad.append(f"after {mv.kind} {mv.stop} {mv.v1}->{mv.v2}: cached totals of "
                       f"{route.vehicle.id} {plan.stats[r]} != recomputed {fresh}")
    return res
search.apply_move = checked
inst = load_day(sys.argv[1], sys.argv[2], 24)
search.improve(initial_plan(inst), 8, int(sys.argv[3]))
print("INVARIANT-BROKEN " + bad[0] if bad else "INVARIANT-OK")
'''


def invariant(work, name, orders, fleet):
    try:
        p = subprocess.run([sys.executable, "-c", INVARIANT, orders, fleet, name.split("_")[1]],
                           cwd=work, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "skipped (timeout)"
    out = p.stdout.strip().splitlines()
    if out and out[-1].startswith("INVARIANT-"):
        return out[-1]
    return "skipped (internals changed: " + (p.stderr.strip().splitlines() or ["?"])[-1] + ")"


def evaluate(work, full=False):
    jobs = days()
    if full:
        jobs.append(("original", os.path.join(work, "data", "orders_2026-09-28.json"),
                     os.path.join(work, "data", "fleet.json"), []))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda j: (j, run_planner(work, j[1], j[2], j[3],
                                                        900 if j[0] == "original" else 50)),
                              jobs))
    report = {}
    for (name, orders, fleet, _), (code, stdout, stderr, routes) in results:
        if routes is None:
            report[name] = {"error": f"no routes written (exit {code}): {stderr[-300:]}"}
            continue
        problems, cost = verify(orders, fleet, routes)
        report[name] = {"problems": problems, "cost": round(cost, 2), "exit": code}
    return report


def main():
    args = sys.argv[1:]
    full = "--full" in args
    make = "--make-expected" in args
    args = [a for a in args if not a.startswith("--")]
    with tempfile.TemporaryDirectory(prefix="sp-oracle-") as tmp:
        work = os.path.join(tmp, "work")
        if make:
            shutil.copytree(os.path.join(HERE, "work"), work)
            subprocess.run(["patch", "-p1", "-s", "-d", work, "-i",
                            os.path.join(HERE, "fix.patch")], check=True)
        else:
            shutil.copytree(args[0], work, ignore=shutil.ignore_patterns("*.pmdb", "out"))
        report = evaluate(work, full)
        if make:
            json.dump({k: v["cost"] for k, v in report.items()}, open(
                os.path.join(HIDDEN, "expected.json"), "w"), indent=1, sort_keys=True)
            print(json.dumps(report, indent=1))
            return 0
        expected = json.load(open(os.path.join(HIDDEN, "expected.json")))
        failures = []
        for name, r in sorted(report.items()):
            if "error" in r:
                failures.append(f"{name}: {r['error']}")
            elif r["problems"]:
                failures.append(f"{name}: {r['problems'][0]} ({len(r['problems'])} problems)")
            elif name in expected and r["cost"] > expected[name] * (1 + TOLERANCE):
                failures.append(f"{name}: cost {r['cost']} > reference {expected[name]} + 1%")
        if not failures:
            name, orders, fleet, _ = days()[0]
            inv = invariant(work, name, orders, fleet)
            if inv.startswith("INVARIANT-BROKEN"):
                failures.append(f"{name}: {inv}")
            else:
                print(f"invariant check: {inv}")
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print(f"PASS: {len(report)} days planned without problems, costs within 1% of the reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
