#!/usr/bin/env python3
"""Generate an HR export for payroll-postmortem and its independent truth.

The truth (what HR's own pay calculation gives) is computed here from the
generator's own notion of employment: a person is employed on a day iff
one of their assignment rows covers it.  It does not import the job.
"""

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import date, timedelta
from fractions import Fraction

PERIOD = (2026, 9)
FIRST = date(2026, 9, 1)
LAST = date(2026, 9, 30)
DAYS = [FIRST + timedelta(n) for n in range(30)]

FIRST_NAMES = "Anna Ben Clara David Elif Felix Greta Hannes Ines Jonas Katarina Lukas Mara Niklas Olga Paul Rosa Sven Tamara Ugur Vera Wim Yasemin Zoran Lea Emre Jana Milan Sofia Tobias".split()
LAST_NAMES = "Albrecht Becker Celik Dietrich Engel Fischer Graf Hoffmann Ivanova Jäger Krause Lorenz Meyer Nowak Ostrowski Peters Quandt Richter Schulz Tran Ulrich Vogel Wagner Yilmaz Zimmermann Kowalski Novak Horvat Popescu Schmid".split()

OFFICE_CC = ["CC-110", "CC-120", "CC-410", "CC-510"]
FLOOR_CC = ["CC-210", "CC-220", "CC-310"]

RULES = dict(
    meal=750, night_bp=2500, sunday_bp=5000, overtime_bp=2500,
    pension_ceiling=845000, health_ceiling=581250,
    ee=dict(pension=930, unemployment=130, health=855, care=180),
    er=dict(pension=930, unemployment=130, health=805, care=180),
    allowance={1: 1209600, 2: 1635600, 3: 2419200, 4: 1209600, 5: 0, 6: 0},
    bands=[(1000000, 1400), (4000000, 2400), (15000000, 4200), (None, 4500)],
)


def iso(d):
    return d.isoformat() if d else None


def iban(rng):
    bban = f"{rng.randrange(10**7, 10**8)}{rng.randrange(10**9, 10**10)}"
    digits = "".join(str(int(c, 36)) for c in bban + "DE00")
    return f"DE{98 - int(digits) % 97:02d}{bban}"


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


class Gen:
    def __init__(self, args):
        self.rng = random.Random(args.seed)
        self.args = args
        self.row_seq = 20000
        self.shapes = Counter()

    def row(self, start, end, pay_type, amount, hours, cc):
        self.row_seq += self.rng.randrange(1, 9)
        r = {"id": f"A{self.row_seq}", "valid_from": iso(start), "valid_to": iso(end),
             "pay_type": pay_type, "weekly_hours": hours, "cost_centre": cc}
        r["monthly_salary" if pay_type == "salaried" else "hourly_rate"] = money(amount)
        return r

    def terms(self, pay_type):
        rng = self.rng
        if pay_type == "salaried":
            hours = rng.choices([40, 40, 40, 38.5, 30, 20], k=1)[0]
            full = rng.choice([rng.randrange(310000, 520000), rng.randrange(450000, 720000),
                               rng.randrange(650000, 1150000)])
            amount = full * Fraction(str(hours)) / 40
            cc = rng.choice(OFFICE_CC) if rng.random() < 0.7 else rng.choice(FLOOR_CC)
            return int(amount) // 100 * 100, hours, cc
        hours = rng.choice([40, 40, 35, 30, 20])
        return rng.randrange(1390, 2450, 5), hours, rng.choice(FLOOR_CC)

    def bump(self, pay_type, amount, cc, change_cc=None):
        rng = self.rng
        if change_cc is None:
            change_cc = rng.random() < 0.4
        if pay_type == "salaried":
            amount = amount + rng.randrange(1, 40) * 1000
        else:
            amount = amount + rng.randrange(5, 120, 5)
        if change_cc:
            pool = OFFICE_CC + FLOOR_CC if pay_type == "salaried" else FLOOR_CC
            cc = rng.choice([c for c in pool if c != cc])
        return amount, cc

    def sept(self, lo, hi):
        return date(2026, 9, self.rng.randint(lo, hi))

    def person_rows(self, shape, pay_type):
        """Assignment rows for one employment shape."""
        rng, a = self.rng, self.args
        amount, hours, cc = self.terms(pay_type)
        hired = date(rng.randint(2012, 2026), 1, 1) + timedelta(rng.randrange(0, 365))
        if hired >= date(2026, 6, 1):
            hired = hired - timedelta(days=400)
        rows = []
        own_start = shape in ("full", "change", "leaver", "gap-follow", "gap-rehire", "gap-inner", "gap-tail")
        if own_start and rng.random() < 0.3:  # an older contiguous row (e.g. last year's raise)
            cut = date(rng.randint(2024, 2026), rng.choice([1, 4, 7]), 1)
            if hired < cut - timedelta(30):
                rows.append(self.row(hired, cut - timedelta(1), pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc)
                hired = cut
        if shape == "full":
            rows.append(self.row(hired, None, pay_type, amount, hours, cc))
        elif shape == "change":  # contiguous change in September
            d = self.sept(2, 30)
            rows.append(self.row(hired, d - timedelta(1), pay_type, amount, hours, cc))
            amount, cc = self.bump(pay_type, amount, cc)
            rows.append(self.row(d, None, pay_type, amount, hours, cc))
        elif shape == "joiner":
            rows = [self.row(self.sept(2, 25), None, pay_type, amount, hours, cc)]
        elif shape == "leaver":
            rows.append(self.row(hired, self.sept(3, 29), pay_type, amount, hours, cc))
        elif shape == "left":
            end = date(2026, 8, 31) - timedelta(rng.randrange(0, 60))
            rows.append(self.row(min(hired, end - timedelta(200)), end, pay_type, amount, hours, cc))
        elif shape == "future":
            rows = [self.row(date(2026, 10, 1), None, pay_type, amount, hours, cc)]
        elif shape == "old-gap":
            end = date(rng.randint(2023, 2025), rng.randint(1, 10), 28)
            rows = [self.row(min(hired, end - timedelta(300)), end, pay_type, amount, hours, cc)]
            amount, cc = self.bump(pay_type, amount, cc)
            rows.append(self.row(end + timedelta(rng.randrange(40, 200)), None, pay_type, amount, hours, cc))
        elif shape.startswith("gap-"):
            kind = shape[4:]
            follow_cc = rng.random() < a.gap_new_cc
            if kind == "follow":  # fixed term ends in September, next contract from October
                end = self.sept(8, 25)
                rows.append(self.row(hired, end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(date(2026, 10, 1), None, pay_type, amount, hours, cc))
            elif kind == "rehire":  # leaves and is re-hired within September
                end = self.sept(3, 14)
                rows.append(self.row(hired, end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(end + timedelta(rng.randrange(4, 14)), None, pay_type, amount, hours, cc))
            elif kind == "start":  # previous contract ended in August, new one starts mid-September
                end = date(2026, 8, rng.randint(10, 31))
                rows.append(self.row(min(hired, end - timedelta(200)), end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(self.sept(7, 21), None, pay_type, amount, hours, cc))
            elif kind == "through":  # ended before September, next contract from October
                end = date(2026, 8, rng.randint(10, 31))
                rows.append(self.row(min(hired, end - timedelta(200)), end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(date(2026, 10, 1), None, pay_type, amount, hours, cc))
            elif kind == "inner":  # three rows with two gaps in September
                e1 = self.sept(5, 10)
                s2 = e1 + timedelta(rng.randrange(3, 6))
                e2 = s2 + timedelta(rng.randrange(3, 6))
                rows.append(self.row(hired, e1, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(s2, e2, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(e2 + timedelta(rng.randrange(3, 8)), None, pay_type, amount, hours, cc))
            elif kind == "head":  # gap at month start: ends late August, next starts Sep 2..5
                end = date(2026, 8, rng.randint(25, 31))
                rows.append(self.row(min(hired, end - timedelta(200)), end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(self.sept(2, 5), None, pay_type, amount, hours, cc))
            elif kind == "tail":  # ends Sep 27..29, next from Oct 1
                end = self.sept(27, 29)
                rows.append(self.row(hired, end, pay_type, amount, hours, cc))
                amount, cc = self.bump(pay_type, amount, cc, follow_cc)
                rows.append(self.row(date(2026, 10, 1), None, pay_type, amount, hours, cc))
            else:
                raise ValueError(shape)
        else:
            raise ValueError(shape)
        rng.shuffle(rows)  # HR exports rows in no particular order
        return rows

    def build(self):
        rng, a = self.rng, self.args
        shapes = []
        for spec in a.gaps.split(",") if a.gaps else []:
            kind, _, count = spec.partition(":")
            for _ in range(int(count)):
                pay_type = "hourly" if rng.random() < a.gap_hourly else "salaried"
                shapes.append((f"gap-{kind}", pay_type))
        base_mix = [("full", 0.80), ("change", 0.075), ("joiner", 0.03), ("leaver", 0.025),
                    ("left", 0.03), ("future", 0.01), ("old-gap", 0.03)]
        while len(shapes) < a.persons:
            shape = rng.choices([s for s, _ in base_mix], [w for _, w in base_mix])[0]
            shapes.append((shape, "hourly" if rng.random() < 0.38 else "salaried"))
        rng.shuffle(shapes)
        persons, timesheets = [], []
        for n, (shape, pay_type) in enumerate(shapes):
            pid = f"P{10001 + n * 3 + rng.randrange(3)}"
            self.shapes[shape] += 1
            rows = self.person_rows(shape, pay_type)
            person = {
                "id": pid,
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "birth_date": iso(date(rng.randint(1960, 2006), rng.randint(1, 12), rng.randint(1, 28))),
                "tax_class": rng.choices([1, 2, 3, 4, 5, 6], [55, 7, 15, 15, 5, 3])[0],
                "iban": iban(rng),
                "assignments": rows,
                "absences": [],
            }
            employed = [d for d in DAYS if covering(rows, d)]
            person["absences"] = self.absences(employed)
            absent = {d for ab in person["absences"] for d in span(ab["from"], ab["to"])}
            if pay_type == "hourly":
                hours = rows[0]["weekly_hours"]
                timesheets.extend(self.shifts(pid, [d for d in employed if d not in absent], hours))
            persons.append(person)
        return {"exported_at": "2026-09-30T18:00:04Z", "period": "2026-09", "persons": persons,
                "timesheets": timesheets}

    def absences(self, employed):
        rng = self.rng
        out = []
        if not employed:
            return out
        for kind, p, lo, hi in (("vacation", 0.25, 2, 9), ("sick", 0.10, 1, 5), ("unpaid", 0.035, 1, 5)):
            if rng.random() < p:
                start = rng.randrange(len(employed))
                length = rng.randint(lo, hi)
                days = [d for d in employed[start:start + length]]
                days = [d for d in days if (d - days[0]).days < length]
                if days and all(not overlaps(o, days) for o in out):
                    out.append({"kind": kind, "from": iso(days[0]), "to": iso(days[-1])})
        return out

    def shifts(self, pid, days, hours):
        rng = self.rng
        skip = 0.06 + (40 - hours) / 40
        pattern = rng.choices(["early", "late", "night", "mixed"], [40, 25, 15, 20])[0]
        works_sundays = rng.random() < 0.15
        out = []
        for d in days:
            wd = d.weekday()
            if wd == 6 and not works_sundays:
                continue
            if wd == 5 and rng.random() < 0.7:
                continue
            if wd < 5 and rng.random() < skip:
                continue
            kind = pattern if pattern != "mixed" else rng.choice(["early", "late", "night"])
            if kind == "early":
                start = 6 * 60 + rng.choice([0, 0, 15, 30, -30])
                length = rng.choice([510, 510, 525, 540, 570, 600, 450])
                brk = 30
            elif kind == "late":
                start = 14 * 60 + rng.choice([0, 0, 30, -60])
                length = rng.choice([510, 510, 540, 480])
                brk = 30
            else:
                start = 22 * 60 + rng.choice([0, 0, -60, -15])
                length = rng.choice([495, 510, 540, 480])
                brk = 45
            end = (start + length) % 1440
            out.append({"person": pid, "date": iso(d), "start": f"{start // 60:02d}:{start % 60:02d}",
                        "end": f"{end // 60:02d}:{end % 60:02d}", "break": brk})
        return out


def span(first, last):
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    return [a + timedelta(n) for n in range((b - a).days + 1)]


def overlaps(absence, days):
    a, b = date.fromisoformat(absence["from"]), date.fromisoformat(absence["to"])
    return any(a <= d <= b for d in days)


def covering(rows, day):
    for r in rows:
        start = date.fromisoformat(r["valid_from"])
        end = date.fromisoformat(r["valid_to"]) if r["valid_to"] else date.max
        if start <= day <= end:
            return r
    return None


# ---------------------------------------------------------------- truth

def cents(text):
    units, _, frac = text.partition(".")
    return int(units) * 100 + int((frac or "0").ljust(2, "0"))


def rhu(x):
    """Round a non-negative Fraction half up."""
    x = Fraction(x)
    return int((x * 2 + 1) // 2)


def pct(amount, bp):
    return rhu(Fraction(amount * bp, 10000))


def night_overlap(start, end):
    total = 0
    for lo, hi in ((-120, 360), (1320, 1800), (2760, 3240)):
        total += max(0, min(end, hi) - max(start, lo))
    return total


def truth_person(person, shifts):
    rows = person["assignments"]
    days = [d for d in DAYS if covering(rows, d)]
    if not days:
        return None
    kind_on = {}
    prec = {"sick": 0, "vacation": 1, "unpaid": 2}
    for ab in person["absences"]:
        for d in span(ab["from"], ab["to"]):
            if d in days and (d not in kind_on or prec[ab["kind"]] < prec[kind_on[d]]):
                kind_on[d] = ab["kind"]
    base = Fraction(0)
    for d in days:
        r = covering(rows, d)
        if r["pay_type"] == "salaried" and kind_on.get(d) != "unpaid":
            base += Fraction(cents(r["monthly_salary"]), 30)
    base = rhu(base)
    pay = Fraction(0)
    prem = Fraction(0)
    weeks = defaultdict(list)
    for s in sorted(shifts, key=lambda s: (s["date"], s["start"])):
        d = date.fromisoformat(s["date"])
        r = covering(rows, d)
        if d not in days or r["pay_type"] != "hourly":
            continue
        rate = cents(r["hourly_rate"])
        h, m = map(int, s["start"].split(":"))
        st = h * 60 + m
        h, m = map(int, s["end"].split(":"))
        en = h * 60 + m
        if en <= st:
            en += 1440
        minutes = en - st - s["break"]
        pay += Fraction(minutes * rate, 60)
        prem += Fraction(night_overlap(st, en) * rate * RULES["night_bp"], 600000)
        if d.weekday() == 6:
            prem += Fraction(minutes * rate * RULES["sunday_bp"], 600000)
        weeks[d.isocalendar()[:2]].append((r, minutes))
    for entries in weeks.values():
        r = entries[0][0]
        extra = sum(m for _, m in entries) - round(r["weekly_hours"] * 60)
        if extra > 0:
            prem += Fraction(extra * cents(r["hourly_rate"]) * RULES["overtime_bp"], 600000)
    for d, kind in kind_on.items():
        r = covering(rows, d)
        if kind in ("sick", "vacation") and d.weekday() < 5 and r["pay_type"] == "hourly":
            pay += Fraction(round(r["weekly_hours"] * 60) * cents(r["hourly_rate"]), 300)
    hourly, premiums = rhu(pay), rhu(prem)
    allowances = RULES["meal"] * sum(1 for d in days if d.weekday() < 5 and d not in kind_on)
    subject = base + hourly + premiums
    n = len(days)
    pc = RULES["pension_ceiling"] if n >= 30 else RULES["pension_ceiling"] * n // 30
    hc = RULES["health_ceiling"] if n >= 30 else RULES["health_ceiling"] * n // 30
    pb, hb = min(subject, pc), min(subject, hc)
    ee = sum(pct(pb if k in ("pension", "unemployment") else hb, bp) for k, bp in RULES["ee"].items())
    er = sum(pct(pb if k in ("pension", "unemployment") else hb, bp) for k, bp in RULES["er"].items())
    taxable = subject - ee
    tax = 0
    if taxable > 0:
        rest = max(0, taxable * 12 - RULES["allowance"][person["tax_class"]])
        acc = 0
        for width, bp in RULES["bands"]:
            part = rest if width is None else min(rest, width)
            acc += part * bp
            rest -= part
        tax = acc // 10000 // 12
    last = covering(rows, days[-1])
    return {
        "cc": last["cost_centre"], "pay_type": last["pay_type"],
        "base_salary": base, "hourly_pay": hourly, "premiums": premiums, "allowances": allowances,
        "gross": subject + allowances, "employee_contributions": ee, "tax": tax,
        "net": subject + allowances - ee - tax, "employer_contributions": er,
    }


COLUMNS = ["base_salary", "hourly_pay", "premiums", "allowances", "gross", "employee_contributions", "tax",
           "net", "employer_contributions"]


def truth(export):
    shifts = defaultdict(list)
    for s in export["timesheets"]:
        shifts[s["person"]].append(s)
    ccs = {}
    totals = Counter()
    heads = 0
    for person in export["persons"]:
        t = truth_person(person, shifts[person["id"]])
        if t is None:
            continue
        row = ccs.setdefault(t["cc"], Counter())
        for c in COLUMNS:
            row[c] += t[c]
            totals[c] += t[c]
        row["headcount"] += 1
        heads += 1
    out = {"cost_centres": {cc: {c: row[c] for c in COLUMNS + ["headcount"]} for cc, row in sorted(ccs.items())},
           "totals": dict({c: totals[c] for c in COLUMNS}, headcount=heads)}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--persons", type=int, default=650)
    p.add_argument("--gaps", default="follow:4,rehire:3,start:2",
                   help="comma-separated kind:count with kinds follow, rehire, start, through, inner, head, tail")
    p.add_argument("--gap-hourly", type=float, default=0.2, help="share of gap persons who are hourly")
    p.add_argument("--gap-new-cc", type=float, default=0.3, help="share of follow-on rows in another cost centre")
    p.add_argument("--out", required=True)
    p.add_argument("--truth-out", required=True)
    args = p.parse_args()
    g = Gen(args)
    export = g.build()
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(export, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(args.truth_out, "w", encoding="utf-8") as fh:
        json.dump({"seed": args.seed, "shapes": dict(sorted(g.shapes.items())), "truth": truth(export)}, fh,
                  indent=2, sort_keys=True)
        fh.write("\n")
    print(dict(sorted(g.shapes.items())))


if __name__ == "__main__":
    main()
