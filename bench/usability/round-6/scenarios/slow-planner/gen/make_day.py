#!/usr/bin/env python3
"""Generates a planning day and the fleet: make_day.py OUT_DIR DATE N_STOPS SEED [N_VANS N_TRUCKS]."""
import json, math, os, random, sys

def make(date, n, seed):
    rng = random.Random(seed)
    centres = [(rng.uniform(-16, 16), rng.uniform(-16, 16), rng.uniform(1.5, 5.0)) for _ in range(14)]
    orders = []
    windows = [(60, 240), (180, 360), (360, 540), (480, 660), (0, 180)]
    for k in range(n):
        if rng.random() < 0.75:
            cx, cy, sd = rng.choice(centres)
            x, y = rng.gauss(cx, sd), rng.gauss(cy, sd)
        else:
            x, y = rng.uniform(-20, 20), rng.uniform(-20, 20)
        kg = max(4, min(260, int(rng.lognormvariate(4.4, 0.5))))
        o = {"id": f"S{k + 1:04d}", "x": round(x, 3), "y": round(y, 3), "kg": kg,
             "service": rng.randint(3, 8)}
        if rng.random() < 0.4:
            o["window"] = list(rng.choice(windows))
        orders.append(o)
    return {"date": date, "horizon": 660, "depot": {"id": "DEPOT", "x": 0.0, "y": -2.0},
            "orders": orders}

def fleet(n_vans, n_trucks):
    vs = [{"id": f"V-{k + 1:02d}", "kind": "van"} for k in range(n_vans)]
    vs += [{"id": f"T-{k + 1:02d}", "kind": "truck"} for k in range(n_trucks)]
    return {"kinds": {"van": {"capacity": 1000, "cost_per_km": 0.45, "fixed_cost": 60.0},
                      "truck": {"capacity": 1600, "cost_per_km": 0.62, "fixed_cost": 85.0}},
            "vehicles": vs}

if __name__ == "__main__":
    out, date, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    nv, nt = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (n // 9, n // 25)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"orders_{date}.json"), "w") as f:
        json.dump(make(date, n, seed), f, indent=0)
    with open(os.path.join(out, "fleet.json"), "w") as f:
        json.dump(fleet(nv, nt), f, indent=1)
