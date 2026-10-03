#!/usr/bin/env python3
"""Generate a points-database snapshot (as of a run's start) and the truth of a correct run.

    python3 gen/gen_db.py --seed S --members N --run-date YYYY-MM-DD --out DB --truth TRUTH.json

The truth is computed here, independently of the job's code: what a correct
nightly run with business date --run-date must report.
"""

import argparse
import json
import random
import sqlite3
from calendar import monthrange
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

SCHEMA = """
CREATE TABLE members (id TEXT PRIMARY KEY, tier TEXT NOT NULL, status TEXT NOT NULL,
    joined_on TEXT NOT NULL, opt_in INTEGER NOT NULL DEFAULT 0);
CREATE TABLE lots (id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, earned_on TEXT NOT NULL,
    source TEXT NOT NULL, points INTEGER NOT NULL, remaining INTEGER NOT NULL, closed_on TEXT);
CREATE INDEX lots_member ON lots (member_id, remaining);
CREATE TABLE activity (id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, business_date TEXT NOT NULL,
    kind TEXT NOT NULL, source TEXT NOT NULL, points INTEGER NOT NULL, ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', posted_at TEXT);
CREATE INDEX activity_day ON activity (business_date, status);
CREATE TABLE ledger (id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, posted_on TEXT NOT NULL,
    kind TEXT NOT NULL, points INTEGER NOT NULL, lot_id INTEGER, created_at TEXT NOT NULL);
CREATE INDEX ledger_member ON ledger (member_id, posted_on);
CREATE TABLE job_runs (id INTEGER PRIMARY KEY, business_date TEXT NOT NULL, started_at TEXT NOT NULL,
    finished_at TEXT, mode TEXT NOT NULL, status TEXT NOT NULL, summary TEXT);
"""

MONTHS = {"purchase": 12, "goodwill": 12, "promo": 3}
MULT = {"basic": (1, 1), "silver": (11, 10), "gold": (5, 4), "platinum": (3, 2)}
TIERS = ["basic", "silver", "gold", "platinum"]
EXEMPT = {"platinum"}
POINT_VALUE = Decimal("0.005")
BREAKAGE = Decimal("0.18")


def month_shift(d, n):
    i = d.year * 12 + d.month - 1 + n
    y, m = divmod(i, 12)
    return date(y, m + 1, 1)


def month_end(d):
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def expiry(source, earned):
    return month_end(month_shift(earned, MONTHS[source]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--members", type=int, default=4800)
    ap.add_argument("--run-date", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--closed-rate", type=float, default=0.011)
    ap.add_argument("--platinum-rate", type=float, default=0.09)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    run = date.fromisoformat(a.run_date)
    first = run.replace(day=1)

    members = []
    for i in range(a.members):
        mid = f"M{204000 + i * 7 + rng.randrange(7):06d}"
        r = rng.random()
        tier = ("platinum" if r < a.platinum_rate else "gold" if r < a.platinum_rate + 0.15
                else "silver" if r < a.platinum_rate + 0.4 else "basic")
        status = "closed" if rng.random() < a.closed_rate else "active"
        joined = first - timedelta(days=rng.randrange(400, 2400))
        members.append({"id": mid, "tier": tier, "status": status, "joined_on": joined.isoformat(),
                        "opt_in": int(rng.random() < 0.7), "activity": rng.uniform(0.15, 0.9)})
    members.sort(key=lambda m: m["id"])

    lots = []  # dicts: id, member, earned, source, points, remaining, closed_on
    ledger = []  # (member, posted_on, kind, points, lot_id, created_at)

    def add_lot(mid, earned, source, points):
        lot = {"id": len(lots) + 1, "member": mid, "earned": earned, "source": source,
               "points": points, "remaining": points, "closed_on": None}
        lots.append(lot)
        return lot

    for m in members:
        for k in range(-16, 1):
            mstart = month_shift(first, k)
            last_day = monthrange(mstart.year, mstart.month)[1] if k < 0 else run.day - 1
            if last_day < 1:
                continue
            if rng.random() < m["activity"]:
                for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
                    earned = mstart.replace(day=rng.randint(1, last_day))
                    base = rng.randint(15, 700)
                    num, den = MULT[m["tier"]]
                    add_lot(m["id"], earned, "purchase", base * num // den)
            if k >= -6 and rng.random() < 0.16:
                add_lot(m["id"], mstart.replace(day=rng.randint(1, last_day)), "promo",
                        rng.choice([100, 150, 200, 250, 300, 500]))
            if rng.random() < 0.015:
                add_lot(m["id"], mstart.replace(day=rng.randint(1, last_day)), "goodwill",
                        rng.choice([50, 100, 200, 300]))

    by_member = {}
    for lot in lots:
        by_member.setdefault(lot["member"], []).append(lot)
    ledger_ts = f"{first.isoformat()}T02:00:00+02:00"
    for m in members:
        mine = by_member.get(m["id"], [])
        for lot in mine:
            exp = expiry(lot["source"], lot["earned"])
            if exp < first and not (m["tier"] in EXEMPT):
                lot["closed_on"] = exp
        # historical burns, soonest-expiring first, over what had not expired
        alive = [l for l in mine if l["closed_on"] is None]
        total = sum(l["remaining"] for l in alive)
        burn = int(total * rng.uniform(0.0, 0.65)) if rng.random() < 0.8 else 0
        this_month_burn = burn // 3 if rng.random() < 0.4 else 0
        for lot in sorted(alive, key=lambda l: (expiry(l["source"], l["earned"]), l["earned"], l["id"])):
            take = min(lot["remaining"], burn)
            lot["remaining"] -= take
            burn -= take
        # what expired earlier was what was left of the lot then; model as fully gone
        for lot in mine:
            if lot["closed_on"] is not None:
                lot["remaining"] = 0
            if lot["earned"] >= first:
                ledger.append((m["id"], lot["earned"].isoformat(), "earn", lot["points"], lot["id"],
                               f"{lot['earned'].isoformat()}T23:5{rng.randrange(10)}:00+02:00"))
        if this_month_burn and run.day > 1:
            day = first.replace(day=rng.randint(1, run.day - 1))
            ledger.append((m["id"], day.isoformat(), "burn", -this_month_burn, None,
                           f"{day.isoformat()}T23:51:00+02:00"))

    # activity for the run's business date (and a few for the next day)
    activity = []
    balance = {m["id"]: sum(l["remaining"] for l in by_member.get(m["id"], [])) for m in members}
    for m in members:
        if m["status"] == "closed":
            continue
        roll = rng.random()
        if roll < 0.17:
            activity.append([m["id"], run, "earn", "purchase", rng.randint(15, 600)])
            if rng.random() < 0.15:
                activity.append([m["id"], run, "earn", "promo", rng.choice([100, 200, 250])])
        if rng.random() < 0.06 and balance[m["id"]] > 200:
            activity.append([m["id"], run, "burn", "purchase",
                             -rng.randint(100, max(100, int(balance[m["id"]] * 0.8)))])
        if rng.random() < 0.004:
            activity.append([m["id"], run, "adjust", "goodwill", rng.choice([100, 250, 500])])
        if rng.random() < 0.0015 and balance[m["id"]] > 50:
            activity.append([m["id"], run, "adjust", "goodwill", -rng.randint(10, 50)])
    actives = [m for m in members if m["status"] == "active"]
    for m in rng.sample(actives, 3):
        activity.append([m["id"], run, "burn", "purchase", -(balance[m["id"]] + rng.randint(50, 400))])
    rng.shuffle(activity)
    for m in rng.sample(actives, 41):
        activity.append([m["id"], run + timedelta(days=1), "earn", "purchase", rng.randint(15, 600)])

    # ---- write the snapshot ----
    conn = sqlite3.connect(a.out)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO members VALUES (?, ?, ?, ?, ?)",
                     [(m["id"], m["tier"], m["status"], m["joined_on"], m["opt_in"]) for m in members])
    conn.executemany("INSERT INTO lots VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [(l["id"], l["member"], l["earned"].isoformat(), l["source"], l["points"], l["remaining"],
                       l["closed_on"].isoformat() if l["closed_on"] else None) for l in lots])
    for n, (mid, day, kind, source, points) in enumerate(activity, 1):
        conn.execute("INSERT INTO activity (id, member_id, business_date, kind, source, points, ref, status) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
                     (n, mid, day.isoformat(), kind, source, points, f"{'POS' if kind != 'adjust' else 'CS'}-"
                      f"{rng.randrange(10**8):08d}"))
    conn.executemany("INSERT INTO ledger (member_id, posted_on, kind, points, lot_id, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?)", sorted(ledger, key=lambda e: (e[1], e[0])))
    for k in range(1, 8):
        d = run - timedelta(days=k)
        conn.execute("INSERT INTO job_runs (business_date, started_at, finished_at, mode, status, summary) "
                     "VALUES (?, ?, ?, ?, 'ok', ?)",
                     (d.isoformat(), f"{d.isoformat()}T23:50:01+02:00", f"{d.isoformat()}T23:51:4{k}+02:00",
                      "month-end" if d == month_end(d) else "daily", f"{rng.randint(900, 1300)} bookings"))
    conn.commit()
    conn.close()

    # ---- truth: a correct run with business date `run` ----
    mtier = {m["id"]: m["tier"] for m in members}
    mstatus = {m["id"]: m["status"] for m in members}
    open_lots = {}
    for l in lots:
        if l["remaining"] > 0:
            open_lots.setdefault(l["member"], []).append(dict(l))
    next_id = len(lots) + 1
    posting = Counter({"earn": 0, "burn": 0, "adjust": 0, "rejected": 0,
                       "earn_points": 0, "burn_points": 0, "adjust_points": 0})
    for mid, day, kind, source, points in activity:
        if day != run:
            continue
        mine = open_lots.setdefault(mid, [])
        if kind == "earn" or (kind == "adjust" and points > 0):
            if kind == "earn" and source == "purchase":
                num, den = MULT[mtier[mid]]
                pts = points * num // den
            else:
                pts = points
            mine.append({"id": next_id, "member": mid, "earned": run,
                         "source": source if kind == "earn" else "goodwill", "points": pts, "remaining": pts})
            next_id += 1
            posting[kind] += 1
            posting["earn_points" if kind == "earn" else "adjust_points"] += pts
            continue
        want = abs(points)
        if sum(l["remaining"] for l in mine) < want:
            posting["rejected"] += 1
            continue
        left = want
        for l in sorted(mine, key=lambda l: (expiry(l["source"], l["earned"]), l["earned"], l["id"])):
            take = min(l["remaining"], left)
            l["remaining"] -= take
            left -= take
        posting[kind] += 1
        if kind == "burn":
            posting["burn_points"] += want
        else:
            posting["adjust_points"] -= want

    month_end_run = run == month_end(run)
    expired = Counter()
    members_expired = forfeited = members_forfeited = exempt = lots_closed = 0
    if month_end_run:
        for m in members:
            mine = [l for l in open_lots.get(m["id"], []) if l["remaining"] > 0]
            if m["status"] == "closed":
                pts = sum(l["remaining"] for l in mine)
                if pts:
                    members_forfeited += 1
                forfeited += pts
                lots_closed += len(mine)
                for l in mine:
                    l["remaining"] = 0
                continue
            if m["tier"] in EXEMPT:
                exempt += 1
                continue
            got = False
            for l in mine:
                if expiry(l["source"], l["earned"]) <= run:
                    expired[l["source"]] += l["remaining"]
                    l["remaining"] = 0
                    lots_closed += 1
                    got = True
            members_expired += got
    by_tier = Counter({t: 0 for t in TIERS})
    by_source = Counter()
    closed_points = expiring = 0
    nxt = month_end(month_shift(run, 1))
    for mid, mine in open_lots.items():
        for l in mine:
            if l["remaining"] <= 0:
                continue
            if mstatus[mid] == "closed":
                closed_points += l["remaining"]
                continue
            by_tier[mtier[mid]] += l["remaining"]
            by_source[l["source"]] += l["remaining"]
            if mtier[mid] not in EXEMPT and expiry(l["source"], l["earned"]) == nxt:
                expiring += l["remaining"]
    outstanding = sum(by_tier.values())
    value = (Decimal(outstanding) * POINT_VALUE * (1 - BREAKAGE)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    closed_members = sum(1 for m in members if m["status"] == "closed")
    truth = {
        "business_date": run.isoformat(),
        "mode": "month-end" if month_end_run else "daily",
        "posting": dict(posting),
        "expiry": {
            "expired_points": sum(expired.values()),
            "expired_by_source": dict(sorted(expired.items())),
            "members_with_expiry": members_expired,
            "forfeited_points": forfeited,
            "closed_accounts_forfeited": members_forfeited,
        },
        "statements": len(members) - closed_members if month_end_run else 0,
        "liability": {
            "outstanding_points": outstanding,
            "outstanding_by_tier": dict(by_tier),
            "outstanding_by_source": dict(sorted(by_source.items())),
            "closed_accounts_points": closed_points,
            "expiring_next_month": {"on": nxt.isoformat(), "points": expiring},
            "value_eur": str(value),
        },
    }
    with open(a.truth, "w") as handle:
        json.dump(truth, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"{a.out}: {len(members)} members, {len(lots)} lots, {len(activity)} activity records; "
          f"truth expired {truth['expiry']['expired_points']}, outstanding {outstanding}")


if __name__ == "__main__":
    main()
