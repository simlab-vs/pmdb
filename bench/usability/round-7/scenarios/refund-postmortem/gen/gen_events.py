#!/usr/bin/env python3
"""Generate a month's provider event export (not shown to agents).

NovaPay accounts migrated to API 2026-08-01 emit a refund lifecycle: a
``refund`` event when the refund is created (status pending, or succeeded for
instant refunds) and further ``refund`` events with the same refund id when its
status changes (succeeded or failed; sometimes a second succeeded event after a
metadata update; rarely succeeded then failed when the bank returns it).

Also writes <out>.truth.json: the providers' settlement statements, computed
with the correct semantics (each refund counted once, at its final status).
"""

import argparse
import calendar
import gzip
import json
import random
from datetime import datetime, timezone

P = argparse.ArgumentParser()
P.add_argument("--seed", type=int, default=1)
P.add_argument("--month", default="2026-09")
P.add_argument("--out", required=True)
P.add_argument("--fx-out", help="also write the FX table CSV here")
P.add_argument("--kestrel", type=int, default=8200)
P.add_argument("--lumen", type=int, default=5600)
P.add_argument("--novapay", type=int, default=6300)
P.add_argument("--np-refund-rate", type=float, default=0.042)
P.add_argument("--migrated", type=float, default=0.5, help="share of NovaPay accounts on the new API")
P.add_argument("--migration-day", type=int, default=12)
P.add_argument("--p-fail", type=float, default=0.07)
P.add_argument("--p-instant", type=float, default=0.10)
P.add_argument("--p-still-pending", type=float, default=0.03)
P.add_argument("--p-meta-update", type=float, default=0.03)
P.add_argument("--p-reversal", type=float, default=0.02)
P.add_argument("--p-extra-processing", type=float, default=0.0)
P.add_argument("--partial-burst", type=float, default=0.15, help="share of refunded charges refunded in several parts")
A = P.parse_args()

rnd = random.Random(A.seed)
year, mon = map(int, A.month.split("-"))
START = calendar.timegm((year, mon, 1, 0, 0, 0))
END = calendar.timegm((year + (mon == 12), mon % 12 + 1, 1, 0, 0, 0))
MIGR = START + (A.migration_day - 1) * 86400 + 6 * 3600

FX = {}  # (day, cur) -> rate (units per EUR), mirrors config/fx/<month>.csv
fx_base = {"GBP": 0.8412, "USD": 1.1046, "CHF": 0.9378, "SEK": 11.402, "PLN": 4.271}


def day(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def build_fx():
    r = random.Random(7)
    d = START - 86400 * 3
    vals = dict(fx_base)
    while d < END + 86400 * 3:
        dd = datetime.fromtimestamp(d, tz=timezone.utc)
        if dd.weekday() < 5:
            for c in vals:
                vals[c] = round(vals[c] * (1 + r.uniform(-0.004, 0.004)), 4)
                FX[(day(d), c)] = vals[c]
        d += 86400


build_fx()
if A.fx_out:
    with open(A.fx_out, "w") as f:
        f.write("date,currency,rate\n")
        for (d, c), v in sorted(FX.items()):
            f.write(f"{d},{c},{v}\n")


def rate(cur, ts):
    dd = day(ts)
    keys = sorted(k[0] for k in FX if k[1] == cur and k[0] <= dd)
    return FX[(keys[-1], cur)]


from decimal import Decimal, ROUND_HALF_EVEN


def to_eur(minor, cur, ts):
    if cur == "EUR":
        return minor
    return int((Decimal(minor) / Decimal(str(rate(cur, ts)))).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def iso_utc(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def naive(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def lumen_date(ts):
    off = rnd.choice([0, 1, 2]) * 3600
    t = datetime.fromtimestamp(ts + off, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{t}+0{off // 3600}:00"


def amount():
    return int(round(rnd.lognormvariate(3.7, 0.8), 2) * 100) + 99


def rid(prefix, n=14):
    return prefix + "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))


def when(lo=START - 4 * 3600, hi=END + 4 * 3600):
    return rnd.randint(lo, hi - 1)


events = []
truth = {p: dict(gross=0, fees=0, refunds=0, disputes=0) for p in ("kestrel", "lumen", "novapay")}


def inwin(ts):
    return START <= ts < END


def emit(ev, ts):
    events.append((ts, ev))


def refund_plan(total):
    if rnd.random() < A.partial_burst:
        k = rnd.randint(2, 3)
        parts = []
        left = total
        for i in range(k - 1):
            p = max(100, int(left * rnd.uniform(0.2, 0.5)))
            parts.append(p)
            left -= p
        parts.append(left if rnd.random() < 0.5 else max(100, left // 2))
        return parts
    if rnd.random() < 0.6:
        return [total]
    return [max(100, int(total * rnd.uniform(0.1, 0.9)))]


# ---------------- Kestrel ----------------
k_accounts = [rid("acct_", 10) for _ in range(9)]
for _ in range(A.kestrel):
    ts = when()
    amt = amount()
    fee = int(round(amt * 0.014)) + 25
    ok = rnd.random() > 0.03
    cid = rid("kch_")
    acct = rnd.choice(k_accounts)
    emit({"id": rid("kev_"), "provider": "kestrel", "type": "charge", "created": ts, "account": acct,
          "data": {"id": cid, "amount": amt, "currency": "eur", "fee": fee, "status": "succeeded" if ok else "failed"}}, ts)
    if ok and inwin(ts):
        truth["kestrel"]["gross"] += amt
        truth["kestrel"]["fees"] += fee
    if ok and rnd.random() < 0.05:
        for part in refund_plan(amt):
            rts = ts + rnd.randint(3600, 9 * 86400)
            emit({"id": rid("kev_"), "provider": "kestrel", "type": "refund", "created": rts, "account": acct,
                  "data": {"id": rid("kre_"), "charge": cid, "amount": part, "currency": "eur", "status": "succeeded"}}, rts)
            if inwin(rts):
                truth["kestrel"]["refunds"] += part
    if ok and rnd.random() < 0.003:
        dts = ts + rnd.randint(86400, 12 * 86400)
        emit({"id": rid("kev_"), "provider": "kestrel", "type": "dispute", "created": dts, "account": acct,
              "data": {"id": rid("kdp_"), "charge": cid, "amount": amt, "currency": "eur", "fee": 1500, "status": "succeeded"}}, dts)
        if inwin(dts):
            truth["kestrel"]["disputes"] += amt
            truth["kestrel"]["fees"] += 1500
# refunds of charges from earlier months
for _ in range(int(A.kestrel * 0.005)):
    rts = when(START, END)
    emit({"id": rid("kev_"), "provider": "kestrel", "type": "refund", "created": rts, "account": rnd.choice(k_accounts),
          "data": {"id": rid("kre_"), "charge": rid("kch_"), "amount": amount(), "currency": "eur", "status": "succeeded"}}, rts)
    truth["kestrel"]["refunds"] += events[-1][1]["data"]["amount"]

# ---------------- Lumen ----------------
l_accounts = ["ShopNordAT", "ShopNordDE", "ShopNordUK", "ShopNordCH"]
cur_of = {"ShopNordAT": "EUR", "ShopNordDE": "EUR", "ShopNordUK": "GBP", "ShopNordCH": "CHF"}
for _ in range(A.lumen):
    ts = when()
    acct = rnd.choice(l_accounts)
    cur = cur_of[acct] if rnd.random() < 0.9 else rnd.choice(["USD", "SEK", "PLN"])
    amt = amount()
    ok = rnd.random() > 0.04
    psp = str(rnd.randint(10 ** 15, 10 ** 16 - 1))
    eur = to_eur(amt, cur, ts)
    fee = 11 + int(round(eur * 0.012))
    emit({"id": rid("LUM-", 12), "provider": "lumen", "eventCode": "AUTHORISATION", "eventDate": lumen_date(ts),
          "pspReference": psp, "merchantAccount": acct, "amount": {"value": amt, "currency": cur},
          "success": "true" if ok else "false", "fees": {"value": fee, "currency": "EUR"}}, ts)
    if ok and inwin(ts):
        truth["lumen"]["gross"] += eur
        truth["lumen"]["fees"] += fee
    if ok and rnd.random() < 0.045:
        for part in refund_plan(amt):
            rts = ts + rnd.randint(3600, 9 * 86400)
            emit({"id": rid("LUM-", 12), "provider": "lumen", "eventCode": "REFUND", "eventDate": lumen_date(rts),
                  "pspReference": str(rnd.randint(10 ** 15, 10 ** 16 - 1)), "originalReference": psp,
                  "merchantAccount": acct, "amount": {"value": part, "currency": cur}, "success": "true"}, rts)
            if inwin(rts):
                truth["lumen"]["refunds"] += to_eur(part, cur, rts)
    if ok and rnd.random() < 0.004:
        dts = ts + rnd.randint(86400, 12 * 86400)
        emit({"id": rid("LUM-", 12), "provider": "lumen", "eventCode": "CHARGEBACK", "eventDate": lumen_date(dts),
              "pspReference": str(rnd.randint(10 ** 15, 10 ** 16 - 1)), "originalReference": psp,
              "merchantAccount": acct, "amount": {"value": amt, "currency": cur}, "success": "true",
              "fees": {"value": 1200, "currency": "EUR"}}, dts)
        if inwin(dts):
            truth["lumen"]["disputes"] += to_eur(amt, cur, dts)
            truth["lumen"]["fees"] += 1200
for _ in range(int(A.lumen * 0.02)):
    ts = when()
    emit({"id": rid("LUM-", 12), "provider": "lumen", "eventCode": rnd.choice(["REPORT_AVAILABLE", "ACCOUNT_UPDATED"]),
          "eventDate": lumen_date(ts), "pspReference": str(rnd.randint(10 ** 15, 10 ** 16 - 1)),
          "merchantAccount": rnd.choice(l_accounts), "success": "true"}, ts)

# ---------------- NovaPay ----------------
n_accounts = [rid("np_acc_", 8) for _ in range(6)]
n_migrated = set(n_accounts[: round(len(n_accounts) * A.migrated)])
shape_counts = {}


def new_api(acct, ts):
    return acct in n_migrated and ts >= MIGR


def np_amount(acct, ts, minor):
    if new_api(acct, ts):
        return f"{minor // 100}.{minor % 100:02d}"
    return minor


def np_event(acct, ts, typ, obj):
    ver = "2026-08-01" if new_api(acct, ts) else "2024-02-15"
    emit({"id": rid("evt_np_", 18), "provider": "novapay", "type": typ, "api_version": ver,
          "created": naive(ts), "account": acct, "data": {"object": obj}}, ts)


def np_refund(acct, cid, part, rts):
    """Emit the refund's events; return the amount the statement counts."""
    ref = rid("npr_")
    base = {"id": ref, "charge": cid, "currency": "EUR"}
    if not new_api(acct, rts):
        np_event(acct, rts, "refund", dict(base, amount=np_amount(acct, rts, part), status="succeeded"))
        shape_counts["old"] = shape_counts.get("old", 0) + 1
        return part if inwin(rts) else 0
    amt = np_amount(acct, rts, part)
    # lifecycles stay within the month (the export window cuts nothing)
    if not (START + 3600 <= rts < END - 5 * 86400) and inwin(rts):
        if rts >= END - 5 * 86400 and rnd.random() < 0.5:
            np_event(acct, rts, "refund", dict(base, amount=amt, status="pending"))
            shape_counts["still_pending"] = shape_counts.get("still_pending", 0) + 1
            return 0
        np_event(acct, rts, "refund", dict(base, amount=amt, status="succeeded"))
        shape_counts["instant"] = shape_counts.get("instant", 0) + 1
        return part
    if not inwin(rts):
        np_event(acct, rts, "refund", dict(base, amount=amt, status="succeeded"))
        return 0
    r = rnd.random()
    t = rts
    seq = []
    if r < A.p_instant:
        seq = ["succeeded"]
        shape = "instant"
    elif r < A.p_instant + A.p_still_pending:
        seq = ["pending"]
        shape = "still_pending"
    elif r < A.p_instant + A.p_still_pending + A.p_fail:
        seq = ["pending", "failed"]
        shape = "pending_failed"
    elif r < A.p_instant + A.p_still_pending + A.p_fail + A.p_reversal:
        seq = ["pending", "succeeded", "failed"]
        shape = "reversal"
    elif r < A.p_instant + A.p_still_pending + A.p_fail + A.p_reversal + A.p_meta_update:
        seq = ["pending", "succeeded", "succeeded"]
        shape = "meta_update"
    else:
        seq = ["pending", "succeeded"]
        shape = "pending_succeeded"
    if A.p_extra_processing and len(seq) > 1 and rnd.random() < A.p_extra_processing:
        seq = seq[:1] + ["processing"] + seq[1:]
        shape += "+processing"
    shape_counts[shape] = shape_counts.get(shape, 0) + 1
    for i, st in enumerate(seq):
        np_event(acct, t, "refund", dict(base, amount=amt, status=st))
        t += rnd.randint(1800, 36 * 3600)
    return part if seq[-1] == "succeeded" else 0


for _ in range(A.novapay):
    ts = when()
    acct = rnd.choice(n_accounts)
    amt = amount()
    fee = int(round(amt * 0.015)) + 20
    ok = rnd.random() > 0.035
    cid = rid("npc_")
    obj = {"id": cid, "amount": np_amount(acct, ts, amt), "currency": "EUR", "status": "succeeded" if ok else "failed"}
    if new_api(acct, ts):
        obj["fee_details"] = {"amount": f"{fee // 100}.{fee % 100:02d}", "currency": "EUR"}
    else:
        obj["fee"] = fee
    np_event(acct, ts, "charge", obj)
    if ok and inwin(ts):
        truth["novapay"]["gross"] += amt
        truth["novapay"]["fees"] += fee
    if ok and rnd.random() < A.np_refund_rate:
        for part in refund_plan(amt):
            rts = ts + rnd.randint(3600, 9 * 86400)
            truth["novapay"]["refunds"] += np_refund(acct, cid, part, rts)
    if ok and rnd.random() < 0.004:
        dts = ts + rnd.randint(86400, 12 * 86400)
        np_event(acct, dts, "dispute", {"id": rid("npd_"), "charge": cid, "amount": np_amount(acct, dts, amt),
                                        "currency": "EUR", "direction": "withdrawal", "status": "succeeded"})
        if inwin(dts):
            truth["novapay"]["disputes"] += amt
        if rnd.random() < 0.3:
            d2 = dts + rnd.randint(86400, 6 * 86400)
            np_event(acct, d2, "dispute", {"id": rid("npd_"), "charge": cid, "amount": np_amount(acct, d2, amt),
                                           "currency": "EUR", "direction": "reinstatement", "status": "succeeded"})
            if inwin(d2):
                truth["novapay"]["disputes"] -= amt
for _ in range(int(A.novapay * 0.004)):
    rts = when(START + 86400, END - 6 * 86400)
    truth["novapay"]["refunds"] += np_refund(rnd.choice(n_accounts), rid("npc_"), amount(), rts)

# ---------------- write ----------------
events.sort(key=lambda e: e[0] + rnd.randint(0, 900))  # archiver order is roughly chronological
lines = [json.dumps(e, separators=(",", ":")) for _, e in events]
for _ in range(max(1, len(lines) // 500)):  # webhook redeliveries
    i = rnd.randrange(len(lines))
    lines.insert(min(len(lines), i + rnd.randint(1, 400)), lines[i])
with gzip.open(A.out, "wt", encoding="utf-8") as f:
    for line in lines:
        f.write(line + "\n")
for p in truth.values():
    p["net"] = p["gross"] - p["fees"] - p["refunds"] - p["disputes"]
with open(A.out + ".truth.json", "w") as f:
    json.dump({"truth": truth, "shapes": shape_counts, "events": len(lines)}, f, indent=2)
print(json.dumps({"truth": truth, "shapes": shape_counts, "events": len(lines)}, indent=1))
