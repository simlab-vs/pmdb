"""Generates random inputs for the invoicing program (hidden from agents)."""

import random

CATEGORIES = ["food", "books", "electronics", "clothing"]


def generate(seed):
  rng = random.Random(seed)
  orders = []
  for k in range(rng.randint(3, 8)):
    lines = []
    for i in range(rng.randint(1, 6)):
      lines.append({
        "sku": f"SKU-{rng.randint(100, 999)}",
        "category": rng.choice(CATEGORIES),
        "unit_price": rng.choice([rng.randint(1, 99), rng.randint(100, 5000), rng.randint(5000, 90000)]),
        "quantity": rng.choice([1, 1, 2, 3, rng.randint(1, 15), rng.randint(5, 120)]),
      })
    order = {
      "id": f"{seed}-{k}",
      "region": rng.choice(["north", "south", "island"]),
      "currency": rng.choice(["EUR", "EUR", "USD", "GBP", "CHF"]),
      "lines": lines,
    }
    coupon = rng.choice([None, None, "WELCOME10", "BIG50", "BOOKWORM", "EXPIRED"])
    if coupon is not None:
      order["coupon"] = coupon
    orders.append(order)
  return orders
