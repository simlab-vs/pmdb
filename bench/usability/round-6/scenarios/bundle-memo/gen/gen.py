"""Generate a quote-run dataset (kept outside work/).

python3 gen.py OUT_DIR --seed N [--orders N] [--own-list BE] [--at-skus K]
"""
import argparse, csv, json, os, random

def money(c): return f"{c // 100}.{c % 100:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--orders", type=int, default=800)
    ap.add_argument("--customers", type=int, default=420)
    ap.add_argument("--own-list", default="AT", help="EUR region with its own price list")
    ap.add_argument("--extra-own", default="", help="second EUR region with its own list")
    ap.add_argument("--diff-skus", type=int, default=7)
    ap.add_argument("--own-share", type=float, default=0.07)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    os.makedirs(os.path.join(a.out, "catalog", "pricelists"), exist_ok=True)

    products = []  # (sku, name, category, groups, base cents)
    teas = ["Assam", "Darjeeling", "Ceylon", "Earl Grey", "Lapsang", "Sencha", "Gyokuro", "Bancha",
            "Genmaicha", "Oolong", "Pu-erh", "Rooibos", "Chai", "Jasmine", "Mint", "Chamomile",
            "Hibiscus", "Lemongrass", "Matcha", "Kukicha", "Keemun", "Yunnan", "Nilgiri", "Kenya",
            "Lady Grey", "Breakfast", "Gunpowder", "White Peony", "Silver Needle", "Hojicha"]
    for i, t in enumerate(teas):
        products.append((f"LT-{101 + i}", f"{t} loose 100 g", "tea", "loose-tea", rnd.choice(range(590, 1490, 50)) + 40 * (i % 2)))
    for i, t in enumerate(["Breakfast", "Earl Grey", "Mint", "Chamomile", "Rooibos", "Green", "Chai", "Fruit", "Ginger", "Lemon", "Detox", "Night"]):
        products.append((f"TB-{201 + i}", f"{t} 20 bags", "tea", "tea-bags", rnd.choice(range(290, 590, 20))))
    for i, t in enumerate(["Brazil", "Colombia", "Ethiopia", "Kenya", "Sumatra", "Guatemala", "Espresso", "Decaf", "Peru", "Honduras", "Yirgacheffe", "Mocca"]):
        products.append((f"CB-{301 + i}", f"{t} beans 250 g", "coffee", "beans", rnd.choice(range(690, 1390, 50))))
    for i, t in enumerate(["Lungo", "Ristretto", "Espresso", "Decaf", "Arpeggio", "Volluto"]):
        products.append((f"CC-{401 + i}", f"{t} capsules x10", "coffee", "", rnd.choice(range(349, 499, 10))))
    acc = [("KT-501", "Glass kettle", 3490), ("KT-502", "Cast iron teapot", 5490), ("CUP-511", "Tea cup", 890),
           ("CUP-512", "Double-wall glass", 1290), ("CUP-513", "Mug", 990), ("INF-521", "Mesh infuser", 690),
           ("INF-522", "Infuser basket", 1190), ("GR-531", "Hand grinder", 3990), ("TIN-541", "Storage tin", 590)]
    for sku, n, p in acc:
        products.append((sku, n, "accessories", "", p))
    base = {p[0]: p[4] for p in products}

    with open(os.path.join(a.out, "catalog", "products.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["sku", "name", "category", "groups", "active"])
        for sku, n, c, g, _ in products: w.writerow([sku, n, c, g, "1"])

    combos = {"BREW-KIT": {"KT-501": 1, "CUP-512": 2}, "STARTER": {"INF-521": 1, "LT-104": 1, "LT-115": 1},
              "GRIND-KIT": {"GR-531": 1, "CB-307": 1}, "TEAPOT-SET": {"KT-502": 1, "CUP-511": 2}}
    def plist(pid, cur, factor, overrides=None):
        prices, combo_prices = {}, {}
        for sku, b in base.items():
            r = int(round(b * factor / 10.0)) * 10 - (10 if cur != "GBP" else 1)
            if overrides and sku in overrides: r = overrides[sku]
            m = int(round(r * 0.92 / 10.0)) * 10
            t = int(round(r * 0.80 / 10.0)) * 10
            prices[sku] = {"retail": money(r), "member": money(m), "trade": money(t)}
        for cid, items in combos.items():
            s = sum(int(round(base[k] * factor / 10.0)) * 10 * q for k, q in items.items())
            if overrides:
                s = sum((overrides.get(k) or int(round(base[k] * factor / 10.0)) * 10) * q for k, q in items.items())
            combo_prices[cid] = money(int(s * 0.85 / 10) * 10 - 10)
        return {"id": pid, "currency": cur, "prices": prices, "combos": combo_prices}

    std = plist("eur-standard", "EUR", 1.0)
    def own_overrides():
        skus = rnd.sample([p[0] for p in products if p[0].startswith(("LT-", "TB-", "CB-"))], a.diff_skus)
        return {s: int(round(base[s] * rnd.uniform(1.06, 1.14) / 10.0)) * 10 - 10 for s in skus}
    lists = [std, plist("chf", "CHF", 1.08), plist("gbp", "GBP", 0.86)]
    own = {a.own_list: f"eur-{a.own_list.lower()}"}
    if a.extra_own: own[a.extra_own] = f"eur-{a.extra_own.lower()}"
    for code, pid in own.items():
        lists.append(plist(pid, "EUR", 1.0, own_overrides()))
    for pl in lists:
        with open(os.path.join(a.out, "catalog", "pricelists", pl["id"] + ".json"), "w") as f:
            json.dump(pl, f, indent=1)

    regions = {
        "DE": ("EUR", "19", "4.90", "49.00"), "AT": ("EUR", "20", "5.90", "59.00"),
        "FR": ("EUR", "20", "6.90", "59.00"), "NL": ("EUR", "21", "5.90", "59.00"),
        "BE": ("EUR", "21", "5.90", "59.00"), "IE": ("EUR", "23", "8.90", "79.00"),
        "CH": ("CHF", "8.1", "9.90", "79.00"), "UK": ("GBP", "20", "6.50", "60.00")}
    reg_json = {}
    for code, (cur, vat, fee, free) in regions.items():
        pl = own.get(code) or {"EUR": "eur-standard", "CHF": "chf", "GBP": "gbp"}[cur]
        reg_json[code] = {"currency": cur, "price_list": pl, "vat": vat, "shipping": {"fee": fee, "free_from": free}}
    with open(os.path.join(a.out, "regions.json"), "w") as f:
        json.dump(reg_json, f, indent=1)

    offers = [
        {"id": "TEA-3FOR2", "kind": "mix", "group": "loose-tea", "buy": 3, "free": 1, "channels": ["web", "store"]},
        {"id": "BAGS-5FOR4", "kind": "mix", "group": "tea-bags", "buy": 5, "free": 1},
        {"id": "BEANS-MEMBER", "kind": "mix", "group": "beans", "buy": 3, "free": 1, "tiers": ["member"]},
        {"id": "CAPS-6", "kind": "bulk", "sku": "CC-401", "qty": 6, "percent": "15"},
        {"id": "CAPS-6B", "kind": "bulk", "sku": "CC-403", "qty": 6, "percent": "15"},
        {"id": "AUTUMN-TINS", "kind": "bulk", "sku": "TIN-541", "qty": 4, "percent": "25", "from": "2026-09-15", "to": "2026-10-15"},
        {"id": "SUMMER-ICED", "kind": "mix", "group": "tea-bags", "buy": 3, "free": 1, "from": "2026-06-01", "to": "2026-08-31"},
    ] + [{"id": cid, "kind": "combo", "items": items} for cid, items in combos.items()]
    with open(os.path.join(a.out, "offers.json"), "w") as f:
        json.dump({"offers": offers}, f, indent=1)

    first = ["Anna", "Lukas", "Marie", "Jonas", "Lea", "Felix", "Sophie", "Paul", "Emma", "Noah", "Mia", "Elias", "Clara", "Theo", "Ida", "Jan"]
    last = ["Müller", "Schmidt", "Huber", "Wagner", "Becker", "Hofer", "Fischer", "Weber", "Gruber", "Bauer", "Klein", "Wolf", "Peeters", "Janssen", "Dubois", "Murphy"]
    cities = {"DE": ["Berlin", "Hamburg", "Köln", "München", "Leipzig"], "AT": ["Wien", "Graz", "Linz", "Salzburg"],
              "FR": ["Paris", "Lyon"], "NL": ["Utrecht", "Amsterdam"], "BE": ["Gent", "Antwerpen"], "IE": ["Dublin"],
              "CH": ["Zürich", "Basel"], "UK": ["London", "Leeds"]}
    other = (1 - 0.52 - a.own_share) / 6
    weights = {"DE": 0.52, a.own_list: a.own_share}
    for c in regions:
        weights.setdefault(c, other)
    customers = []
    for i in range(a.customers):
        country = rnd.choices(list(weights), list(weights.values()))[0]
        tier = rnd.choices(["retail", "member", "trade"], [0.55, 0.35, 0.10])[0]
        vat_id = f"{country}{rnd.randrange(10**8, 10**9)}" if tier == "trade" and rnd.random() < 0.8 else ""
        customers.append({"id": f"C-{1001 + i}", "name": f"{rnd.choice(first)} {rnd.choice(last)}",
                          "city": rnd.choice(cities[country]), "country": country, "tier": tier, "vat_id": vat_id})
    with open(os.path.join(a.out, "customers.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "city", "country", "tier", "vat_id"]); w.writeheader()
        for c in customers: w.writerow(c)

    skus = [p[0] for p in products]
    popular = [s for s in skus if s.startswith("LT-")][:12]
    with open(os.path.join(a.out, "orders.jsonl"), "w") as f:
        for i in range(a.orders):
            c = rnd.choice(customers)
            nlines = rnd.choices([1, 2, 3, 4, 5], [0.2, 0.3, 0.25, 0.15, 0.1])[0]
            lines = []
            for _ in range(nlines):
                pool = popular if rnd.random() < 0.45 else skus
                sku = rnd.choice(pool)
                qty = rnd.choices([1, 2, 3, 6], [0.6, 0.25, 0.1, 0.05])[0]
                lines.append({"sku": sku, "qty": qty})
            ch = rnd.choices(["web", "store", "phone"], [0.7, 0.2, 0.1])[0]
            f.write(json.dumps({"id": f"Q-{30001 + i}", "customer": c["id"], "channel": ch, "lines": lines}) + "\n")

main()
