#!/usr/bin/env python3
"""Generate a billing dataset (customers, tariffs, meter events, feeds).

Kept outside work/: it names the needles.

  python3 make_data.py --seed 2026 --accounts 3100 --needle tx_legacy_to_ml --out DIR

Needle kinds (each applied to one fresh account):
  tx_legacy_to_ml    legacy account, Telemetrix meter (reported under the legacy
                     id) exchanged mid-month for a Meterline smart meter (current id)
  gs_legacy_to_ml    same with a GridSense old meter
  gs_to_ml           non-legacy account, GridSense ("AC004127") -> Meterline ("AC-004127")
  mixed_closing      legacy GridSense account whose closing read is delivered under
                     the current id
Writes DIR/data/... and DIR/truth.json (MDM metered total, needles).
"""

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

PERIOD_START = date(2026, 9, 1)
PERIOD_END = date(2026, 10, 1)

FIRST = "Olivia Amelia Isla Ava Mia Ivy Lily Isabella Rosie Sophia Grace Freya Noah Oliver George Arthur Muhammad Leo Harry Oscar Archie Henry Theo Jack Charlie Jacob Thomas Alfie Finley Joshua Mohammed Priya Aisha Zara Wojciech Agnieszka Siobhan Ciaran Eilidh Rhys".split()
LAST = "Smith Jones Taylor Brown Williams Wilson Johnson Davies Patel Wright Robinson Thompson Evans Walker White Roberts Green Hall Thomas Clarke Jackson Wood Harris Edwards Turner Martin Cooper Hill Ward Hughes Moore Clark King Harrison Lewis Baker Lee Allen Morris Khan Scott Watson Davis Parker James Bennett Young Phillips Richardson Mitchell Bailey Carter Cook Singh Shaw Bell Collins Morgan Kelly Begum Miller Cox Hussain Marshall Simpson Price Anderson Adams Wilkinson Ali Ahmed Foster Ellis Murphy Chapman Mason Gray Richards Webb Griffiths Hunt Palmer Campbell Holmes Mills Rogers Barnes Knight Matthews Barker Powell Stevens Kaur Fisher Butler Dixon Russell Harvey Pearson Graham".split()
TRADES = "Bakery Garage Dental Surgery Florist Pharmacy Joinery Cafe Print Works Vets Opticians Butchers Brewery Laundrette Hotel Nursery Gym Studio Motors Builders Logistics Plastics Engineering Cold Store".split(" ")

TARIFFS = {
    "tariffs": {
        "DOM-STD": {
            "description": "Standard variable (domestic)",
            "standing_charge_per_day": 0.5122,
            "tiers": [{"up_to_kwh": 180, "rate": 0.3104}, {"up_to_kwh": None, "rate": 0.2756}],
            "vat_rate": 0.05,
        },
        "DOM-FIX24": {
            "description": "Fixed price 24 months (domestic)",
            "standing_charge_per_day": 0.4870,
            "tiers": [{"up_to_kwh": None, "rate": 0.2650}],
            "vat_rate": 0.05,
        },
        "DOM-GREEN": {
            "description": "Renewable fixed (domestic)",
            "standing_charge_per_day": 0.4990,
            "tiers": [{"up_to_kwh": None, "rate": 0.2788}],
            "vat_rate": 0.05,
        },
        "BUS-SME": {
            "description": "Small business",
            "standing_charge_per_day": 1.0950,
            "tiers": [
                {"up_to_kwh": 1500, "rate": 0.2690},
                {"up_to_kwh": 6000, "rate": 0.2480},
                {"up_to_kwh": None, "rate": 0.2310},
            ],
            "levy_per_kwh": 0.00775,
            "vat_rate": 0.20,
        },
        "BUS-HV": {
            "description": "Large business, half-hourly settled",
            "standing_charge_per_day": 4.8500,
            "tiers": [{"up_to_kwh": None, "rate": 0.2105}],
            "levy_per_kwh": 0.00775,
            "vat_rate": 0.20,
        },
    }
}

SEASONAL_SEPT = 0.87


class Gen:
    def __init__(self, seed, n_accounts):
        self.rng = random.Random(seed)
        self.n = n_accounts
        self.used_numbers = set()
        self.used_legacy = set()
        self.used_meters = set()
        self.customers = []
        self.events = []
        self.tx = []
        self.gs = []
        self.ml = []
        self.metered = Decimal(0)
        self.meter_kwh = {}
        self.needles = []

    # identifiers -------------------------------------------------------
    def account_number(self):
        while True:
            n = self.rng.randint(1000, 389999)
            if n not in self.used_numbers:
                self.used_numbers.add(n)
                return n

    def legacy_number(self):
        while True:
            n = self.rng.randint(10000, 59999)
            if n not in self.used_legacy:
                self.used_legacy.add(n)
                return n

    def meter_id(self, vendor):
        while True:
            if vendor == "tx":
                m = f"TX{self.rng.randint(1000000, 9999999)}"
            elif vendor == "gs":
                m = f"G{self.rng.randint(10, 99)}K{self.rng.randint(100000, 999999)}"
            else:
                m = f"ML-{self.rng.randint(0x100000, 0xFFFFFF):06X}"
            if m not in self.used_meters:
                self.used_meters.add(m)
                return m

    # time helpers ------------------------------------------------------
    def read_time(self, day, vendor):
        if vendor == "ml":
            return datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
        return datetime(day.year, day.month, day.day, self.rng.randint(6, 18), self.rng.randint(0, 59))

    # emitting readings -------------------------------------------------
    def emit(self, vendor, raw_id, meter, when, value, kind, dials=6, ratio=None):
        if vendor == "tx":
            reason = {"routine": self.rng.choice(["RT"] * 9 + ["KS"]), "removal": "AU", "install": "EI"}[kind]
            text = f"{value:.1f}".replace(".", ",")
            self.tx.append([raw_id, meter, when.strftime("%d.%m.%Y %H:%M"), text, str(dials), reason])
        elif vendor == "gs":
            rt = {"routine": self.rng.choice(["scheduled"] * 12 + ["special"]), "removal": "final", "install": "initial"}[kind]
            self.gs.append([raw_id, meter, when.isoformat(timespec="minutes"), f"{value:.2f}",
                            "" if ratio is None else str(ratio), rt])
        else:
            ev = {"routine": self.rng.choice(["periodic"] * 15 + ["on_demand"]), "removal": "decommissioning",
                  "install": "commissioning"}[kind]
            self.ml.append({"acct": raw_id, "device": meter, "ts": int(when.timestamp()), "wh": int(round(value * 1000)), "event": ev})

    def quantum(self, vendor):
        return {"tx": Decimal("0.1"), "gs": Decimal("0.01"), "ml": Decimal("0.001")}[vendor]

    def register_series(self, vendor, start_day, end_day, kwh, dials, ratio, interim=0):
        """Register values at start, interim points and end; returns list of (day, value) and metered kWh."""
        q = self.quantum(vendor)
        mult = Decimal(str(ratio or 1))
        advance = (Decimal(str(kwh)) / mult).quantize(q)
        if vendor == "ml":
            advance += Decimal(self.rng.randint(0, 99)) / 1000
        capacity = Decimal(10) ** dials if vendor != "ml" else None
        if vendor == "ml":
            start = Decimal(self.rng.randint(200_000, 40_000_000)) / 1000
        elif vendor == "tx" and dials == 5 and self.rng.random() < 0.08:
            start = (capacity - Decimal(self.rng.randint(1, 1500)) / 10 * 3).quantize(q)
        else:
            top = int(capacity) // 3
            start = (Decimal(self.rng.randint(1000, top)) + Decimal(self.rng.randint(0, 99)) / 100).quantize(q)
        points = [(start_day, start)]
        span = (end_day - start_day).days
        if interim and span > 4:
            cut = self.rng.randint(2, span - 2)
            part = (advance * Decimal(cut) / Decimal(span)).quantize(q)
            points.append((start_day + timedelta(days=cut), start + part))
        points.append((end_day, start + advance))
        if capacity is not None:
            points = [(d, v % capacity) for d, v in points]
        return points, advance * mult

    def add_meter(self, vendor, raw_id, start_day, end_day, kwh, dials=6, ratio=None, first_kind="routine",
                  last_kind="routine", interim=0, drop=None, record=True):
        meter = self.meter_id(vendor)
        points, metered = self.register_series(vendor, start_day, end_day, kwh, dials, ratio, interim)
        n = len(points)
        for i, (day, value) in enumerate(points):
            if drop == "first" and i == 0 or drop == "last" and i == n - 1 or drop == "all":
                continue
            kind = first_kind if i == 0 else last_kind if i == n - 1 else "routine"
            self.emit(vendor, raw_id, meter, self.read_time(day, vendor), float(value), kind, dials, ratio)
        if record and drop is None:
            self.metered += metered
            self.meter_kwh[meter] = str(metered)
        return meter, metered

    # accounts ----------------------------------------------------------
    def customer(self, segment, legacy):
        number = self.account_number()
        acc = f"AC-{number:06d}"
        if segment == "business":
            name = f"{self.rng.choice(LAST)} {self.rng.choice(TRADES)} Ltd"
            eac = self.rng.choice([self.rng.randint(15000, 60000)] * 4 + [self.rng.randint(60000, 260000)])
            tariff = "BUS-HV" if eac > 150000 else "BUS-SME"
        else:
            name = f"{self.rng.choice(FIRST)} {self.rng.choice(LAST)}"
            eac = self.rng.randint(1200, 7200)
            tariff = self.rng.choice(["DOM-STD"] * 6 + ["DOM-FIX24"] * 3 + ["DOM-GREEN"])
        legacy_id = f"NW-{self.legacy_number()}" if legacy else ""
        row = {"account": acc, "name": name, "segment": segment, "tariff": tariff, "eac_kwh": str(eac),
               "move_in": "", "move_out": "", "legacy_id": legacy_id}
        self.customers.append(row)
        return row

    def raw_id(self, row, vendor, use_legacy=None):
        legacy = row["legacy_id"] if use_legacy is None else (row["legacy_id"] if use_legacy else "")
        if vendor == "ml":
            return row["account"]
        ident = legacy or row["account"]
        if vendor == "gs":
            return ident.replace("-", "")
        return ident

    def month_kwh(self, row, days=30):
        base = int(row["eac_kwh"]) / 365 * days * SEASONAL_SEPT
        return round(base * self.rng.uniform(0.55, 1.45), 1)

    def vendor_for(self, row):
        if row["segment"] == "business" and int(row["eac_kwh"]) > 60000:
            return "gs"
        r = self.rng.random()
        if row["legacy_id"]:
            return "tx" if r < 0.7 else "gs"
        return "tx" if r < 0.5 else "gs" if r < 0.72 else "ml"

    def ordinary(self, row):
        vendor = self.vendor_for(row)
        rid = self.raw_id(row, vendor)
        ratio = None
        if vendor == "gs" and int(row["eac_kwh"]) > 60000:
            ratio = self.rng.choice([20, 40, 80])
        dials = self.rng.choice([5, 5, 6]) if vendor == "tx" else 6
        start, end = PERIOD_START, PERIOD_END
        r = self.rng.random()
        if r < 0.012:
            row["move_in"] = (PERIOD_START + timedelta(days=self.rng.randint(3, 25))).isoformat()
            start = date.fromisoformat(row["move_in"])
        elif r < 0.024:
            row["move_out"] = (PERIOD_START + timedelta(days=self.rng.randint(3, 25))).isoformat()
            end = date.fromisoformat(row["move_out"])
        elif r < 0.034:
            row["move_out"] = (PERIOD_START - timedelta(days=self.rng.randint(5, 60))).isoformat()
            return
        elif r < 0.04:
            row["move_in"] = (PERIOD_START - timedelta(days=self.rng.randint(1, 3))).isoformat()
        kwh = self.month_kwh(row, (end - start).days)
        drop = None
        q = self.rng.random()
        if q < 0.018:
            drop = "first"
        elif q < 0.03:
            drop = "last"
        elif q < 0.034:
            drop = "all"
        interim = 1 if self.rng.random() < 0.12 and drop is None else 0
        self.add_meter(vendor, rid, start, end, kwh, dials, ratio, interim=interim, drop=drop)
        if vendor == "gs" and drop is None and self.rng.random() < 0.01:
            self.gs.append(list(self.gs[-1]))

    def exchange(self, row, old_vendor, new_vendor, old_legacy=None, new_legacy=None, needle=None):
        day = PERIOD_START + timedelta(days=self.rng.randint(6, 24))
        kwh1 = self.month_kwh(row, (day - PERIOD_START).days)
        kwh2 = self.month_kwh(row, (PERIOD_END - day).days)
        old_id = self.raw_id(row, old_vendor, old_legacy)
        new_id = self.raw_id(row, new_vendor, new_legacy)
        old_meter, m1 = self.add_meter(old_vendor, old_id, PERIOD_START, day, kwh1,
                                       5 if old_vendor == "tx" else 6, None, last_kind="removal")
        new_meter, m2 = self.add_meter(new_vendor, new_id, day, PERIOD_END, kwh2,
                                       6, None, first_kind="install")
        self.events.append({"event": "exchange", "account": row["account"], "old_meter": old_meter,
                            "new_meter": new_meter, "date": day.isoformat()})
        if needle:
            self.needles.append({"kind": needle, "account": row["account"], "legacy_id": row["legacy_id"],
                                 "old_meter": old_meter, "old_kwh": str(m1), "new_meter": new_meter,
                                 "new_kwh": str(m2), "date": day.isoformat()})

    def mixed_closing(self, row):
        vendor = "gs"
        meter = self.meter_id("gs")
        points, metered = self.register_series("gs", PERIOD_START, PERIOD_END, self.month_kwh(row), 6, None)
        (d0, v0), (d1, v1) = points
        self.emit("gs", self.raw_id(row, "gs"), meter, self.read_time(d0, "gs"), float(v0), "routine")
        self.emit("gs", self.raw_id(row, "gs", use_legacy=False), meter, self.read_time(d1, "gs"), float(v1), "routine")
        self.metered += metered
        self.needles.append({"kind": "mixed_closing", "account": row["account"], "legacy_id": row["legacy_id"],
                             "meter": meter, "kwh": str(metered)})

    def build(self, needles, plain_exchanges):
        rows = []
        for _ in range(self.n):
            segment = "business" if self.rng.random() < 0.09 else "domestic"
            rows.append(self.customer(segment, self.rng.random() < 0.11))
        special = set()
        for kind in needles:
            while True:
                row = self.rng.choice(rows)
                if row["account"] in special or row["segment"] != "domestic":
                    continue
                if kind in ("tx_legacy_to_ml", "gs_legacy_to_ml", "mixed_closing") and not row["legacy_id"]:
                    continue
                if kind == "gs_to_ml" and row["legacy_id"]:
                    continue
                break
            special.add(row["account"])
            if kind == "tx_legacy_to_ml":
                self.exchange(row, "tx", "ml", needle=kind)
            elif kind == "gs_legacy_to_ml":
                self.exchange(row, "gs", "ml", needle=kind)
            elif kind == "gs_to_ml":
                self.exchange(row, "gs", "ml", needle=kind)
            elif kind == "mixed_closing":
                self.mixed_closing(row)
            else:
                raise SystemExit(f"unknown needle {kind}")
        plain = 0
        while plain < plain_exchanges:
            row = self.rng.choice(rows)
            if row["account"] in special:
                continue
            special.add(row["account"])
            pairs = [("tx", "tx"), ("tx", "ml"), ("gs", "gs")] if not row["legacy_id"] else [("tx", "tx"), ("gs", "gs")]
            old, new = pairs[plain % len(pairs)]
            self.exchange(row, old, new)
            plain += 1
        for row in rows:
            if row["account"] not in special:
                self.ordinary(row)

    def write(self, out):
        data = out / "data"
        feeds = data / "feeds"
        feeds.mkdir(parents=True, exist_ok=True)
        order = sorted(self.customers, key=lambda r: r["account"])
        cols = ["account", "name", "segment", "tariff", "eac_kwh", "move_in", "move_out", "legacy_id"]
        with open(data / "customers.csv", "w") as f:
            f.write(",".join(cols) + "\n")
            for r in order:
                f.write(",".join(r[c] for c in cols) + "\n")
        (data / "tariffs.json").write_text(json.dumps(TARIFFS, indent=2) + "\n")
        self.rng.shuffle(self.events)
        with open(data / "meter_events.csv", "w") as f:
            f.write("event,account,old_meter,new_meter,date\n")
            for e in self.events:
                f.write(f"{e['event']},{e['account']},{e['old_meter']},{e['new_meter']},{e['date']}\n")
        self.rng.shuffle(self.tx)
        with open(feeds / "tx_2026-09.csv", "w") as f:
            f.write("ACCOUNT;METER;READ_AT;REGISTER;DIALS;REASON\n")
            for r in sorted(self.tx, key=lambda r: (r[2][6:10], r[2][3:5], r[2][0:2], r[2][11:])):
                f.write(";".join(r) + "\n")
        with open(feeds / "gs_2026-09.csv", "w") as f:
            f.write("account_ref,meter_serial,timestamp,reading_kwh,ct_ratio,read_type\n")
            for r in sorted(self.gs, key=lambda r: r[2]):
                f.write(",".join(r) + "\n")
        with open(feeds / "ml_2026-09.jsonl", "w") as f:
            for r in sorted(self.ml, key=lambda r: (r["ts"], r["device"])):
                f.write(json.dumps(r) + "\n")
        truth = {"mdm_metered_kwh": str(self.metered.quantize(Decimal("0.1"))), "needles": self.needles,
                 "readings": len(self.tx) + len(self.gs) + len(self.ml)}
        (out / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
        return truth


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--accounts", type=int, default=3100)
    p.add_argument("--needle", action="append", default=[])
    p.add_argument("--plain-exchanges", type=int, default=5)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    g = Gen(a.seed, a.accounts)
    g.build(a.needle, a.plain_exchanges)
    print(json.dumps(g.write(a.out), indent=2))


if __name__ == "__main__":
    main()
