#!/usr/bin/env python3
"""Generate a day's card-events queue dump and its ground truth.

The truth is computed from the unique card events (not from the messages),
independently of the ledger code: what the issuing bank's settlement and
balance figures are.

    python3 gen_queue.py --seed S --out dump.jsonl.gz [options]
writes dump.jsonl.gz and dump.jsonl.gz.truth.json
"""

import argparse
import gzip
import json
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

PROGRAMME = "KPE-01"
FX_FEE_BP = 175
ATM_FEE = 250
HOME = "DE"

GROUPS = {}
for g, codes in {
    "retail": ["5311", "5411", "5499", "5651", "5691", "5732", "5812", "5814", "5912", "5942", "5999"],
    "travel": ["3000", "3501", "4511", "4722", "7011", "7512"],
    "transport": ["4111", "4121", "4131", "4784", "7523"],
    "fuel": ["5541", "5542"],
    "cash": ["6011"],
    "online": ["4816", "4899", "5734", "5815", "5816", "5817", "5818"],
}.items():
    for c in codes:
        GROUPS[c] = g

RATES = {"USD": Decimal("1.1712"), "GBP": Decimal("0.8731"), "CHF": Decimal("0.9364"), "PLN": Decimal("4.2710")}

ONLINE_MCCS = ["5411", "5411", "5411", "5812", "5814", "5814", "5912", "5999", "5651", "5732",
               "4816", "5815", "5818", "5942", "4121", "4511", "7011", "5541"]


def cents(d):
    return int((d * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def money(minor):
    return f"{minor // 100}.{minor % 100:02d}"


class Gen:
    def __init__(self, args):
        self.a = args
        self.r = random.Random(args.seed)
        day = datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)
        self.day = day
        self.prev = (day - timedelta(days=1)).date().isoformat()
        self.events = []          # unique notifications: dict(type, created, data)
        self.auth_codes = set()
        self.refs = set()
        self.merchants = {}
        for mcc in set(ONLINE_MCCS) | {"6011", "5542", "7011", "4111", "4784", "7523"}:
            self.merchants[mcc] = [
                {"id": f"M{self.r.randrange(10**7, 10**8)}", "name": f"Merchant {mcc}-{i}", "mcc": mcc,
                 "country": "DE" if self.r.random() < 0.8 else self.r.choice(["AT", "NL", "FR", "ES"])}
                for i in range(12)
            ]
        self.transit = [
            {"id": "M40110001", "name": "Rhein-Main Verkehrsverbund", "mcc": "4111", "country": "DE"},
            {"id": "M40110002", "name": "Stadtwerke Mainz Mobilitaet", "mcc": "4111", "country": "DE"},
        ]
        self.tolls = [{"id": "M47840001", "name": "Brueckenmaut Rheinstrasse", "mcc": "4784", "country": "DE"}]
        self.parking = [{"id": "M75230001", "name": "Parkhaus Zentrum", "mcc": "7523", "country": "DE"},
                        {"id": "M75230002", "name": "ParkRing Messe", "mcc": "7523", "country": "DE"}]

    def ts(self, seconds):
        return (self.day + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def code(self):
        while True:
            c = "".join(self.r.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6))
            if c not in self.auth_codes:
                self.auth_codes.add(c)
                return c

    def ref(self):
        while True:
            c = "7" + "".join(self.r.choice("0123456789") for _ in range(22))
            if c not in self.refs:
                self.refs.add(c)
                return c

    def add(self, etype, t, data):
        self.events.append({"type": etype, "t": t, "data": data})

    def purchase_amount(self, mcc):
        r = self.r
        if mcc in ("5812", "5814"):
            return r.randint(350, 6800)
        if mcc in ("4511", "7011"):
            return r.randint(6000, 42000)
        if mcc == "5541":
            return r.randint(2500, 9500)
        return r.randint(199, 15900)

    def card_day(self, card):
        r, a = self.r, self.a
        # top-ups
        for _ in range(r.choices([0, 1, 2], [0.7, 0.26, 0.04])[0]):
            t = r.randint(0, 86000)
            self.add("topup", t, {"topup_id": f"tu_{uuid.UUID(int=r.getrandbits(128)).hex[:16]}",
                                  "card": card, "amount": money(r.choice([2000, 5000, 5000, 10000, 15000, 20000, r.randint(1000, 30000)])),
                                  "currency": "EUR", "source": r.choice(["sepa", "card", "voucher"]),
                                  "transaction_time": self.ts(t)})
        # online purchases
        for _ in range(r.choices([0, 1, 2, 3, 4], [0.25, 0.3, 0.25, 0.12, 0.08])[0]):
            mcc = r.choice(ONLINE_MCCS)
            self.online(card, mcc)
        if r.random() < a.p_fuel:
            self.fuel(card)
        if r.random() < a.p_hotel:
            self.online(card, "7011", over=True)
        if r.random() < a.p_split:
            self.split(card)
        if r.random() < a.p_atm:
            self.online(card, "6011", amount=r.choice([2000, 5000, 10000, 20000]))
        if r.random() < a.p_refund:
            m = r.choice(self.merchants[r.choice(ONLINE_MCCS)])
            t = r.randint(0, 86000)
            amt = self.purchase_amount(m["mcc"])
            self.add("refund", t, {"network_ref": self.ref(), "card": card, "amount": money(amt), "currency": "EUR",
                                   "billing_amount": money(amt), "merchant": m, "transaction_time": self.ts(t - 86400 * r.randint(1, 20))})
        if r.random() < a.p_late:
            m = r.choice(self.merchants[r.choice(ONLINE_MCCS)])
            t = r.randint(0, 86000)
            amt = self.purchase_amount(m["mcc"])
            self.add("clearing", t, {"network_ref": self.ref(), "auth_code": self.code(), "card": card,
                                     "amount": money(amt), "currency": "EUR", "billing_amount": money(amt),
                                     "merchant": m, "transaction_time": self.ts(t - 86400 * r.randint(1, 4)), "final": True})
        if r.random() < a.p_rider:
            self.rider(card)

    def money_pair(self, amt_eur, foreign):
        if not foreign:
            return money(amt_eur), "EUR", money(amt_eur)
        cur = self.r.choice(list(RATES))
        local = cents(Decimal(amt_eur) / 100 * RATES[cur])
        billing = cents(Decimal(local) / 100 / RATES[cur])
        return money(local), cur, money(billing)

    def online(self, card, mcc, over=False, amount=None):
        r, a = self.r, self.a
        m = r.choice(self.merchants[mcc])
        amt = amount or self.purchase_amount(mcc)
        foreign = m["country"] != "DE" and r.random() < 0.5 or r.random() < 0.04
        amount_s, cur, billing = self.money_pair(amt, foreign)
        if cur == "EUR":
            billing_minor = amt
        else:
            billing_minor = int(Decimal(billing) * 100)
        t = r.randint(0, 86000)
        code = self.code()
        base = {"card": card, "amount": amount_s, "currency": cur, "billing_amount": billing,
                "merchant": m, "transaction_time": self.ts(t)}
        self.add("authorization", t, {"auth_code": code, **base})
        u = r.random()
        if u < a.p_reverse:
            self.add("authorization.reversal", t + r.randint(30, 3000), {"auth_code": code, **base, "transaction_time": self.ts(t + 20)})
            return
        if u < a.p_reverse + a.p_open:
            return  # cleared on a later day: hold stays open
        ct = t + (r.randint(1, 4) if r.random() < a.p_quick else r.randint(600, 30000))
        clearing = dict(base)
        if over:
            extra = r.randint(500, 6000)
            clearing["billing_amount"] = money(billing_minor + extra)
            clearing["amount"] = clearing["billing_amount"] if cur == "EUR" else money(cents(Decimal(billing_minor + extra) / 100 * RATES[cur]))
        self.add("clearing", min(ct, 86390), {"network_ref": self.ref(), "auth_code": code, **clearing, "final": True})

    def fuel(self, card):
        r = self.r
        m = r.choice(self.merchants["5542"])
        t = r.randint(0, 86000)
        code = self.code()
        self.add("authorization", t, {"auth_code": code, "card": card, "amount": "100.00", "currency": "EUR",
                                      "billing_amount": "100.00", "merchant": m, "transaction_time": self.ts(t)})
        actual = r.randint(1800, 9800)
        self.add("clearing", t + r.randint(2, 900), {"network_ref": self.ref(), "auth_code": code, "card": card,
                                                     "amount": money(actual), "currency": "EUR", "billing_amount": money(actual),
                                                     "merchant": m, "transaction_time": self.ts(t), "final": True})

    def split(self, card):
        r = self.r
        m = r.choice(self.merchants["5999"])
        t = r.randint(0, 70000)
        code = self.code()
        total = r.randint(3000, 25000)
        self.add("authorization", t, {"auth_code": code, "card": card, "amount": money(total), "currency": "EUR",
                                      "billing_amount": money(total), "merchant": m, "transaction_time": self.ts(t)})
        first = r.randint(1000, total - 1000)
        if first * 2 == total:
            first += 1
        second = total - first if r.random() < 0.6 else r.randint(500, total - first)
        if second == first:
            second -= 1
        final2 = r.random() < 0.7
        self.add("clearing", t + r.randint(600, 8000), {"network_ref": self.ref(), "auth_code": code, "card": card,
                 "amount": money(first), "currency": "EUR", "billing_amount": money(first), "merchant": m,
                 "transaction_time": self.ts(t), "final": False})
        self.add("clearing", t + r.randint(9000, 16000), {"network_ref": self.ref(), "auth_code": code, "card": card,
                 "amount": money(second), "currency": "EUR", "billing_amount": money(second), "merchant": m,
                 "transaction_time": self.ts(t), "final": final2})

    def rider(self, card):
        """Offline transit fares, tolls and parking: presented the next day, date only, no auth."""
        r, a = self.r, self.a
        op = r.choice(self.transit)
        n = r.choices([1, 2, 3, 4], [0.35, 0.42, 0.13, 0.10])[0]
        usual = r.choice([290, 290, 340, 180])
        fares = []
        for i in range(n):
            fare = usual if r.random() < 0.85 else r.choice([180, 290, 340, 520])
            fares.append(fare)
        if a.distinct_offline:
            seen = set()
            out = []
            for f in fares:
                while f in seen:
                    f += 10
                seen.add(f)
                out.append(f)
            fares = out
        extra = []
        if r.random() < 0.12:
            toll = self.tolls[0]
            k = r.choice([1, 2, 2])
            amts = [420] * k
            if a.distinct_offline:
                amts = [420 + 10 * i for i in range(k)]
            extra += [(toll, x) for x in amts]
        if r.random() < 0.10:
            p = r.choice(self.parking)
            amts = [r.choice([150, 200, 300, 450, 600]) for _ in range(r.choice([1, 2]))]
            if a.distinct_offline and len(amts) == 2 and amts[0] == amts[1]:
                amts[1] += 50
            extra += [(p, x) for x in amts]
        batch_t = {m["id"]: r.randint(3600 * 3, 3600 * 7) for m in [op] + self.tolls + self.parking}
        for merchant, amt in [(op, f) for f in fares] + extra:
            t = batch_t[merchant["id"]] + r.randint(0, 40)
            self.add("clearing", t, {"network_ref": self.ref(), "card": card, "amount": money(amt), "currency": "EUR",
                                     "billing_amount": money(amt), "merchant": merchant,
                                     "transaction_time": self.prev, "final": True})

    # ---------------------------------------------------------------- truth
    def truth(self):
        totals = Counter()
        counts = Counter()
        groups = {}
        movement = Counter()
        posted_cards = set()
        auths = {}
        for e in self.events:
            if e["type"] == "authorization":
                d = e["data"]
                auths[(d["card"], d["auth_code"])] = {"card": d["card"], "amount": int(Decimal(d["billing_amount"]) * 100),
                                                     "used": 0, "closed": False}
        for e in self.events:
            d = e["data"]
            typ = e["type"]
            if typ == "topup":
                amt = int(Decimal(d["amount"]) * 100)
                totals["topup"] += amt; counts["topup"] += 1; movement[d["card"]] += amt; posted_cards.add(d["card"])
            elif typ == "refund":
                amt = int(Decimal(d["billing_amount"]) * 100)
                totals["refund"] += amt; counts["refund"] += 1; movement[d["card"]] += amt; posted_cards.add(d["card"])
            elif typ == "authorization.reversal":
                auths[(d["card"], d["auth_code"])]["closed"] = True
            elif typ == "clearing":
                amt = int(Decimal(d["billing_amount"]) * 100)
                totals["clearing"] += amt; counts["clearing"] += 1; movement[d["card"]] -= amt; posted_cards.add(d["card"])
                g = GROUPS.get(d["merchant"]["mcc"], "other")
                gg = groups.setdefault(g, {"count": 0, "amount": 0})
                gg["count"] += 1; gg["amount"] += amt
                if d["currency"] != "EUR":
                    fee = int((Decimal(amt) * FX_FEE_BP / Decimal(10000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
                    if fee:
                        totals["fx_fee"] += fee; counts["fx_fee"] += 1; movement[d["card"]] -= fee
                if d["merchant"]["mcc"] == "6011" and d["merchant"]["country"] != HOME:
                    totals["atm_fee"] += ATM_FEE; counts["atm_fee"] += 1; movement[d["card"]] -= ATM_FEE
                key = (d["card"], d.get("auth_code"))
                if key in auths:
                    h = auths[key]
                    h["used"] += amt
                    if d.get("final", True):
                        h["closed"] = True
        held = Counter()
        open_holds = 0
        for h in auths.values():
            rem = 0 if h["closed"] else max(0, h["amount"] - h["used"])
            if rem:
                held[h["card"]] += rem
                open_holds += 1
        cards = {}
        for card in sorted(posted_cards | set(held)):
            cards[card] = {"movement": movement.get(card, 0), "held": held.get(card, 0)}
        kinds = ["clearing", "refund", "topup", "fx_fee", "atm_fee"]
        return {
            "totals": {**{k: totals[k] for k in kinds}, "net_movement": sum(movement.values()), "held": sum(held.values())},
            "counts": {**{k: counts[k] for k in kinds}, "open_holds": open_holds},
            "clearings_by_group": dict(sorted(groups.items())),
            "cards": cards,
        }

    # ---------------------------------------------------------------- delivery
    def messages(self):
        r, a = self.r, self.a
        deliveries = []
        start_ms = int(self.day.timestamp() * 1000)

        def envelope(e, programme=PROGRAMME):
            return {"event_id": "evt_" + uuid.UUID(int=r.getrandbits(128)).hex[:24], "type": e["type"],
                    "created": self.ts(e["t"]), "programme": programme, "data": e["data"]}

        def message(body, t):
            return {"MessageId": str(uuid.UUID(int=r.getrandbits(128))),
                    "ReceiptHandle": "AQEB" + uuid.UUID(int=r.getrandbits(128)).hex,
                    "Attributes": {"SentTimestamp": str(start_ms + int(t * 1000)), "ApproximateReceiveCount": "1"},
                    "Body": json.dumps(body, separators=(",", ":"))}

        stats = Counter()
        for e in self.events:
            t = e["t"] + r.uniform(0.2, 25)
            body = envelope(e)
            delay_original = 0
            if r.random() < a.p_resend:
                stats["resend"] += 1
                resend = dict(body, event_id="evt_" + uuid.UUID(int=r.getrandbits(128)).hex[:24])
                rt = t + r.uniform(30, 900)
                if r.random() < a.p_resend_first:
                    delay_original = rt - t + r.uniform(5, 600)
                    stats["resend_first"] += 1
                deliveries.append((rt, message(resend, rt)))
            if e["type"] == "clearing" and e["data"].get("auth_code") and r.random() < a.p_ooo:
                t -= r.uniform(5, 40)
                stats["ooo"] += 1
            if e["type"] == "authorization.reversal" and r.random() < a.p_ooo:
                t = e["t"] - r.uniform(1, 30)
            t += delay_original
            m = message(body, t)
            deliveries.append((t, m))
            if r.random() < a.p_redeliver:
                stats["redeliver"] += 1
                again = json.loads(json.dumps(m))
                again["Attributes"]["ApproximateReceiveCount"] = "2"
                again["ReceiptHandle"] = "AQEB" + uuid.UUID(int=r.getrandbits(128)).hex
                rt = t + r.uniform(30, 600) if r.random() < 0.9 else t + r.uniform(0.01, 2)
                deliveries.append((rt, again))
        for _ in range(a.other_programme):
            e = {"type": "topup", "t": r.randint(0, 86000),
                 "data": {"topup_id": f"tu_{r.getrandbits(64):016x}", "card": f"KG{r.randrange(10**8):08d}",
                          "amount": "25.00", "currency": "EUR", "source": "sepa", "transaction_time": self.ts(0)}}
            deliveries.append((e["t"], message(envelope(e, "KPG-02"), e["t"])))
        deliveries.sort(key=lambda d: d[0])
        return [m for _, m in deliveries], stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--date", default="2026-09-28")
    p.add_argument("--cards", type=int, default=3200)
    p.add_argument("--p-rider", type=float, default=0.16)
    p.add_argument("--distinct-offline", action="store_true", help="no two identical offline fares per card")
    p.add_argument("--p-resend", type=float, default=0.015)
    p.add_argument("--p-resend-first", type=float, default=0.3)
    p.add_argument("--p-redeliver", type=float, default=0.02)
    p.add_argument("--p-ooo", type=float, default=0.06)
    p.add_argument("--p-quick", type=float, default=0.15)
    p.add_argument("--p-reverse", type=float, default=0.04)
    p.add_argument("--p-open", type=float, default=0.12)
    p.add_argument("--p-fuel", type=float, default=0.08)
    p.add_argument("--p-hotel", type=float, default=0.02)
    p.add_argument("--p-split", type=float, default=0.03)
    p.add_argument("--p-atm", type=float, default=0.05)
    p.add_argument("--p-refund", type=float, default=0.03)
    p.add_argument("--p-late", type=float, default=0.03)
    p.add_argument("--other-programme", type=int, default=37)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    g = Gen(a)
    cards = sorted({f"KP{g.r.randrange(10**8):08d}" for _ in range(a.cards)})
    for card in cards:
        g.card_day(card)
    msgs, stats = g.messages()
    with gzip.open(a.out, "wt", encoding="utf-8") as fh:
        for m in msgs:
            fh.write(json.dumps(m, separators=(",", ":")) + "\n")
    truth = g.truth()
    # Diagnostics: offline fares that collide on the ledger's transaction fields.
    seen, collide, collide_amt = set(), 0, 0
    for e in g.events:
        d = e["data"]
        if e["type"] == "clearing" and not d.get("auth_code"):
            k = (d["card"], d["merchant"]["id"], d["amount"], d["transaction_time"])
            if k in seen:
                collide += 1
                collide_amt += int(Decimal(d["billing_amount"]) * 100)
            seen.add(k)
    meta = {"seed": a.seed, "messages": len(msgs), "events": len(g.events), "delivery": dict(stats),
            "offline_collisions": collide, "offline_collision_amount": collide_amt}
    with open(a.out + ".truth.json", "w") as fh:
        json.dump({"meta": meta, "truth": truth}, fh, indent=1, sort_keys=True)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
