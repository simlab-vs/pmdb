"""Generates random inputs for the route planner (hidden from agents)."""

import random


def generate(seed):
  rng = random.Random(seed)
  width, height = rng.randint(3, 6), rng.randint(3, 6)
  intersections = {}
  for x in range(width):
    for y in range(height):
      intersections[f"{chr(65 + x)}{y}"] = (x * 100, y * 100)

  streets = []
  # Avenues run north-south and roads east-west; some blocks are missing or one-way.
  for x in range(width):
    for y in range(height - 1):
      if rng.random() < 0.85:
        a, b = f"{chr(65 + x)}{y}", f"{chr(65 + x)}{y + 1}"
        if rng.random() < 0.3:
          a, b = b, a
        streets.append({"name": f"Avenue {chr(65 + x)}", "from": a, "to": b,
                        "seconds": rng.randint(20, 90), "one_way": rng.random() < 0.3})
  for y in range(height):
    for x in range(width - 1):
      if rng.random() < 0.85:
        a, b = f"{chr(65 + x)}{y}", f"{chr(65 + x + 1)}{y}"
        if rng.random() < 0.3:
          a, b = b, a
        streets.append({"name": f"Road {y}", "from": a, "to": b,
                        "seconds": rng.randint(20, 90), "one_way": rng.random() < 0.3})

  names = sorted(intersections)
  trips = [rng.sample(names, 2) for _ in range(rng.randint(3, 7))]
  return {"intersections": intersections, "streets": streets, "trips": trips}
