"""Generate an input directory for the invoicing run (kept outside work/).

python3 make_data.py OUT --seed N --customers N [--heavy-growth POS ...] [--heavy-starter POS ...]

--heavy-growth/--heavy-starter put a customer whose usage makes the next plan cheaper
(so the upgrade suggestion, the path that mutates the shared tiers, runs) at the given
positions (0-based, in invoicing order).
"""
import argparse, csv, json, random
from pathlib import Path

PLANS = {
  "plans": {
    "starter": {"name": "Starter", "base_fee": 29, "metrics": {
      "api_requests": {"label": "API requests", "unit": "requests", "model": "volume", "included": 50000,
        "tiers": [{"from": 0, "to": 250000, "unit_price": 0.0012}, {"from": 250000, "to": None, "unit_price": 0.0011}]},
      "storage_gb": {"label": "storage", "unit": "GB-months", "model": "graduated", "aggregate": "average", "included": 10,
        "tiers": [{"from": 0, "to": None, "unit_price": 0.025}]},
      "seats": {"label": "seats", "unit": "seats", "model": "per_unit", "aggregate": "max", "included": 3, "unit_price": 9}}},
    "growth": {"name": "Growth", "base_fee": 249, "metrics": {
      "api_requests": {"label": "API requests", "unit": "requests", "model": "volume", "included": 200000,
        "tiers": [{"from": 0, "to": 1000000, "unit_price": 0.0009}, {"from": 1000000, "to": 5000000, "unit_price": 0.0008},
                  {"from": 5000000, "to": None, "unit_price": 0.0007}]},
      "storage_gb": {"label": "storage", "unit": "GB-months", "model": "graduated", "aggregate": "average", "included": 100,
        "tiers": [{"from": 0, "to": 1000, "unit_price": 0.023}, {"from": 1000, "to": None, "unit_price": 0.021}]},
      "egress_gb": {"label": "data transfer", "unit": "GB", "model": "graduated", "included": 100,
        "tiers": [{"from": 0, "to": 10000, "unit_price": 0.08}, {"from": 10000, "to": None, "unit_price": 0.06}]},
      "seats": {"label": "seats", "unit": "seats", "model": "per_unit", "aggregate": "max", "included": 10, "unit_price": 8}}},
    "scale": {"name": "Scale", "base_fee": 990, "metrics": {
      "api_requests": {"label": "API requests", "unit": "requests", "model": "volume", "included": 500000,
        "tiers": [{"from": 0, "to": 2000000, "unit_price": 0.0008}, {"from": 2000000, "to": 10000000, "unit_price": 0.0006},
                  {"from": 10000000, "to": 50000000, "unit_price": 0.00045}, {"from": 50000000, "to": None, "unit_price": 0.0003}]},
      "storage_gb": {"label": "storage", "unit": "GB-months", "model": "graduated", "aggregate": "average", "included": 500,
        "tiers": [{"from": 0, "to": 5000, "unit_price": 0.021}, {"from": 5000, "to": 50000, "unit_price": 0.019},
                  {"from": 50000, "to": None, "unit_price": 0.017}]},
      "egress_gb": {"label": "data transfer", "unit": "GB", "model": "graduated", "included": 1000,
        "tiers": [{"from": 0, "to": 10000, "unit_price": 0.07}, {"from": 10000, "to": 100000, "unit_price": 0.05},
                  {"from": 100000, "to": None, "unit_price": 0.04}]},
      "seats": {"label": "seats", "unit": "seats", "model": "per_unit", "aggregate": "max", "included": 25, "unit_price": 7}}},
    "legacy_pro": {"name": "Pro (legacy)", "base_fee": 99, "retired": True, "metrics": {
      "api_requests": {"label": "API requests", "unit": "requests", "model": "graduated", "included": 100000,
        "tiers": [{"from": 0, "to": 1000000, "unit_price": 0.001}, {"from": 1000000, "to": None, "unit_price": 0.0009}]},
      "seats": {"label": "seats", "unit": "seats", "model": "per_unit", "aggregate": "max", "included": 5, "unit_price": 10}}},
  }
}
SETTINGS = {"seller_country": "DE", "base_currency": "EUR", "invoice_prefix": "INV", "minimum_invoice": 5,
  "payment_terms_days": 30,
  "eu_countries": ["AT", "BE", "DE", "ES", "FR", "IE", "IT", "NL", "PL", "SE"],
  "vat_rates": {"AT": 0.2, "BE": 0.21, "DE": 0.19, "ES": 0.21, "FR": 0.2, "IE": 0.23, "IT": 0.22, "NL": 0.21, "PL": 0.23, "SE": 0.25}}
COUNTRIES = [("DE", "EUR", 30), ("FR", "EUR", 10), ("NL", "EUR", 8), ("AT", "EUR", 5), ("ES", "EUR", 5), ("IT", "EUR", 5),
             ("SE", "EUR", 3), ("PL", "EUR", 3), ("IE", "EUR", 3), ("GB", "GBP", 14), ("US", "USD", 12), ("CH", "EUR", 2)]
WORDS = "Acme Nordlicht Blue Harbor Pixel Kestrel Orbit Lumen Vector Fjord Quartz Atlas Cobalt Ember Granite Helix Juniper Krypton Linden Meridian Nimbus Onyx Polar Rivet Sable Tundra Umber Vireo Willow Zephyr Alder Birch Cedar Delta Echo Falcon Garnet Heron Iris Jasper".split()
SUFFIX = ["GmbH", "SAS", "B.V.", "Ltd", "Inc.", "AG", "S.L.", "S.r.l.", "AB", "Labs", "Systems", "Analytics", "Software"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--customers", type=int, default=1200)
    ap.add_argument("--period", default="2026-09")
    ap.add_argument("--heavy-growth", type=int, nargs="*", default=[])
    ap.add_argument("--heavy-starter", type=int, nargs="*", default=[])
    ap.add_argument("--contracts", type=int, default=6)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    out = a.out; out.mkdir(parents=True, exist_ok=True)
    (out / "plans.json").write_text(json.dumps(PLANS, indent=2) + "\n")
    (out / "settings.json").write_text(json.dumps(SETTINGS, indent=2) + "\n")
    (out / "fx.json").write_text(json.dumps({"base": "EUR", "periods": {
        "2026-08": {"GBP": 0.8571, "USD": 1.0912}, a.period: {"GBP": 0.8634, "USD": 1.0874}}}, indent=2) + "\n")
    year, month = map(int, a.period.split("-"))
    import calendar
    ndays = calendar.monthrange(year, month)[1]
    days = [f"{year:04d}-{month:02d}-{d:02d}" for d in range(1, ndays + 1)]
    countries = [c for c in COUNTRIES for _ in range(c[2])]
    customers = []
    names = set()
    for i in range(a.customers):
        cid = f"C{10001 + i}"
        if i in a.heavy_growth:
            plan = "growth"
        elif i in a.heavy_starter:
            plan = "starter"
        else:
            plan = rnd.choices(["starter", "growth", "scale", "legacy_pro"], [48, 34, 15, 3])[0]
        while True:
            name = f"{rnd.choice(WORDS)} {rnd.choice(WORDS)} {rnd.choice(SUFFIX)}"
            if name not in names: names.add(name); break
        country, currency, _ = rnd.choice(countries)
        b2b = rnd.random() < 0.8
        vat = f"{country}{rnd.randint(100000000, 999999999)}" if b2b and country not in ("US", "CH") else ""
        disc = rnd.choice([0] * 12 + [5, 10, 15]) if plan != "starter" else 0
        customers.append({"id": cid, "name": name, "country": country, "currency": currency, "plan": plan,
                          "segment": "self_serve", "vat_id": vat, "discount_pct": disc,
                          "suspended": "yes" if rnd.random() < 0.01 else ""})
        if i in a.heavy_growth or i in a.heavy_starter:
            customers[-1]["suspended"] = ""
    scale_ids = [c for c in customers if c["plan"] == "scale"]
    contracts = []
    for k, c in enumerate(rnd.sample(scale_ids, min(a.contracts, len(scale_ids)))):
        c["segment"] = "enterprise"; c["suspended"] = ""
        contracts.append({"id": f"K-{2024 + k % 3}-{100 + k}", "customer": c["id"], "metric": "api_requests",
                          "committed_units": rnd.choice([10, 15, 20, 30, 60]) * 1000000,
                          "discount_pct": rnd.choice([5, 8, 10, 12]), "start": "2026-01-01", "end": "2026-12-31"})
    contracts.append({"id": "K-2023-077", "customer": scale_ids[0]["id"], "metric": "api_requests",
                      "committed_units": 5000000, "discount_pct": 5, "start": "2023-01-01", "end": "2025-12-31"})
    # monthly totals
    def monthly(c, i):
        p = c["plan"]
        if i in a.heavy_growth:
            api = rnd.randint(7_000_000, 9_000_000); sto = rnd.randint(200, 2000); egr = rnd.randint(500, 3000); seats = rnd.randint(8, 20)
        elif i in a.heavy_starter:
            api = rnd.randint(900_000, 1_400_000); sto = rnd.randint(5, 60); egr = 0; seats = rnd.randint(2, 6)
        elif p == "starter":
            api = int(rnd.lognormvariate(10.8, 1.0)); api = min(api, 240_000); sto = rnd.randint(0, 40); egr = 0; seats = rnd.randint(1, 5)
        elif p == "growth":
            api = int(rnd.lognormvariate(13.4, 0.7)); api = min(api, 2_800_000); sto = rnd.randint(20, 2500); egr = rnd.randint(0, 2500); seats = rnd.randint(3, 30)
        elif p == "scale":
            api = int(rnd.lognormvariate(15.2, 0.7)); sto = rnd.randint(300, 80000); egr = rnd.randint(200, 150000); seats = rnd.randint(10, 120)
        else:
            api = int(rnd.lognormvariate(12.5, 0.9)); sto = 0; egr = 0; seats = rnd.randint(1, 8)
        if c["segment"] == "enterprise":
            api = rnd.randint(8_000_000, 70_000_000)
        return api, sto, egr, seats
    rows = []
    rid = 0
    def add(day, cid, metric, q):
        nonlocal rid
        rid += 1
        rows.append([day, cid, metric, q, f"r{rid:07d}"])
    for i, c in enumerate(customers):
        api, sto, egr, seats = monthly(c, i)
        if rnd.random() < 0.03 and i not in a.heavy_growth and i not in a.heavy_starter:
            continue
        weights = [rnd.random() + 0.3 for _ in days]
        tw = sum(weights)
        split = [int(api * w / tw) for w in weights]
        split[-1] += api - sum(split)
        esplit = [int(egr * w / tw) for w in weights]
        esplit[-1] += egr - sum(esplit)
        for d, day in enumerate(days):
            add(day, c["id"], "api_requests", split[d])
            if sto or c["plan"] != "legacy_pro":
                add(day, c["id"], "storage_gb", round(sto * (0.9 + 0.2 * d / ndays), 2))
            if c["plan"] in ("growth", "scale") or egr:
                add(day, c["id"], "egress_gb", esplit[d])
            add(day, c["id"], "seats", max(1, seats - rnd.randint(0, 2)))
        if rnd.random() < 0.02:
            add(days[rnd.randrange(ndays)], c["id"], "api_requests", -rnd.randint(1000, 20000))
    rnd.shuffle(rows)
    dups = [list(r) for r in rnd.sample(rows, len(rows) // 300)]
    rows.extend(dups)
    prev = f"{year:04d}-{month - 1:02d}-{ndays - 1:02d}" if month > 1 else f"{year - 1}-12-30"
    for _ in range(40):
        rid += 1
        rows.append([prev, rnd.choice(customers)["id"], "api_requests", rnd.randint(100, 9000), f"r{rid:07d}"])
    rows.sort(key=lambda r: (r[0], r[4]))
    with open(out / f"usage_{a.period}.csv", "w", newline="") as h:
        w = csv.writer(h); w.writerow(["date", "customer", "metric", "quantity", "record_id"]); w.writerows(rows)
    with open(out / "customers.csv", "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["id", "name", "country", "currency", "plan", "segment", "vat_id", "discount_pct", "suspended"])
        w.writeheader(); w.writerows(customers)
    (out / "contracts.json").write_text(json.dumps(contracts, indent=2) + "\n")
    changes = []
    for c in rnd.sample([c for c in customers if c["plan"] in ("growth", "scale") and c["segment"] != "enterprise"], 25):
        frm = {"growth": "starter", "scale": "growth"}[c["plan"]]
        changes.append({"customer": c["id"], "effective": rnd.choice(days[1:]), "from_plan": frm, "to_plan": c["plan"]})
    changes.sort(key=lambda r: r["effective"])
    with open(out / "plan_changes.csv", "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["customer", "effective", "from_plan", "to_plan"]); w.writeheader(); w.writerows(changes)

main()
