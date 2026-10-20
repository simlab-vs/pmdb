"""Generates random inputs for the warehouse program (hidden from agents)."""

import random

CATEGORIES = ["tools", "garden", "food", "paint", "fixings"]


def generate(seed):
  rng = random.Random(seed)
  n_sites = rng.choice([2, 2, 3, 3, 4])
  sites = []
  for i in range(n_sites):
    site = {"code": "S" + "ABCD"[i], "zone": rng.randint(0, 5)}
    if rng.random() < 0.03:
      site["capacity"] = rng.randint(60, 250)
    sites.append(site)

  perishable = rng.random() < 0.3
  strict = rng.random() < 0.12
  rush = rng.random() < 0.1
  items = []
  for i in range(rng.randint(4, 12)):
    category = rng.choice(CATEGORIES)
    item = {
      "sku": f"{category[:2].upper()}{100 + i * 7 + rng.randint(0, 6)}",
      "category": category,
      "std_cost": rng.choice([rng.randint(50, 900), rng.randint(900, 20000)]),
      "reorder_point": rng.choice([0, 0, rng.randint(2, 20)]),
      "weight": rng.choice(["light", "light", "medium", "heavy", "bulky"]),
    }
    if perishable and category == "food" and rng.random() < 0.7:
      item["shelf_life"] = rng.randint(3, 15)
    if strict and rng.random() < 0.4:
      item["backorder"] = False
    items.append(item)

  codes = [s["code"] for s in sites]
  skus = [it["sku"] for it in items]
  costs = {it["sku"]: it["std_cost"] for it in items}
  days = rng.randint(10, 40)
  events = []
  order_ids = []
  order_skus = {}
  n_events = rng.randint(50, 220)
  weights = [30, 20, 24, 3, 7, 6, 4, 3]
  kinds = ["receipt", "order", "pick", "cancel", "return", "transfer", "adjust", "count"]
  for k in range(n_events):
    day = rng.randint(1, days)
    kind = rng.choices(kinds, weights)[0]
    sku = rng.choice(skus)
    site = rng.choice(codes)
    if kind == "receipt":
      base = costs[sku]
      cost = max(1, base + rng.randint(-base // 5, base // 5))
      events.append({"day": day, "type": "receipt", "site": site, "sku": sku,
                     "qty": rng.choice([rng.randint(1, 10), rng.randint(10, 60), rng.randint(50, 200)]),
                     "unit_cost": cost})
    elif kind == "order":
      order_id = f"O{seed}-{k}"
      order_ids.append((order_id, day))
      lines = []
      for _ in range(rng.choice([1, 1, 2, 3, 4])):
        lines.append({"sku": rng.choice(skus), "qty": rng.choice([1, 2, 3, rng.randint(1, 25)])})
      order_skus[order_id] = [line["sku"] for line in lines]
      event = {"day": day, "type": "order", "order": order_id, "site": site, "lines": lines}
      if rush and rng.random() < 0.15:
        event["priority"] = 0
      elif rng.random() < 0.6:
        event["priority"] = rng.randint(1, 9)
      events.append(event)
    elif kind == "pick" and order_ids:
      order_id, placed = rng.choice(order_ids)
      event = {"day": rng.randint(placed, days), "type": "pick", "order": order_id}
      if rng.random() < 0.25:
        event["limit"] = rng.randint(1, 8)
      events.append(event)
    elif kind == "cancel" and order_ids:
      order_id, placed = rng.choice(order_ids)
      events.append({"day": rng.randint(placed, days), "type": "cancel", "order": order_id})
    elif kind == "return" and order_ids:
      order_id, placed = rng.choice(order_ids)
      if rng.random() < 0.9:
        sku = rng.choice(order_skus[order_id])
      events.append({"day": rng.randint(placed, days), "type": "return", "order": order_id, "sku": sku,
                     "qty": rng.randint(1, 6),
                     "condition": rng.choice(["good", "good", "good", "damaged"])})
    elif kind == "transfer" and len(codes) > 1:
      source, target = rng.sample(codes, 2)
      events.append({"day": day, "type": "transfer", "from": source, "to": target, "sku": sku,
                     "qty": rng.randint(1, 40)})
    elif kind == "adjust":
      events.append({"day": day, "type": "adjust", "site": site, "sku": sku,
                     "delta": rng.choice([-1, -2, -5, 1, 3, rng.randint(-30, 30) or 1])})
    elif kind == "count":
      events.append({"day": day, "type": "count", "site": site, "sku": sku,
                     "counted": rng.randint(0, 80)})
  return {"sites": sites, "items": items, "events": events}
