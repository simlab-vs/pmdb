"""Generates random inputs for the scheduler program (hidden from agents)."""

import random

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def generate(seed):
  rng = random.Random(seed)
  rooms = {}
  for r in range(rng.randint(2, 4)):
    bookings = []
    for _ in range(rng.randint(2, 9)):
      day = rng.choice(DAYS[:5] if rng.random() < 0.9 else DAYS)
      hour = rng.choice([rng.randint(7, 18), rng.randint(9, 16)])
      minute = rng.choice([0, 0, 15, 30, 45])
      booking = {
        "start": f"{day} {hour:02d}:{minute:02d}",
        "duration": rng.choice([15, 30, 30, 45, 60, 60, 90, 120, rng.randint(10, 600)]),
      }
      if rng.random() < 0.25:
        booking["every_days"] = rng.choice([1, 1, 2, 7])
      bookings.append(booking)
    rooms[f"R{r + 1}"] = bookings
  return {"rooms": rooms, "minimum": rng.choice([15, 30, 45, 60, 90])}
