"""Aggregate query.pmdb's export: rows used for days after they ended."""
import json
from collections import defaultdict
from fractions import Fraction

past = defaultdict(list)
for line in open("lookups.jsonl"):
    call = json.loads(line)
    segments, day = call["positional"]
    row = call["returned"]
    if day > row["valid_to"]:
        later = [s["valid_from"] for s in segments if s["valid_from"] > row["valid_to"]]
        past[call["positional"][0][0]["person"]].append((day, row, later[0] if later else None, call["location"]))
excess = Fraction(0)
print(f"{len(past)} persons paid on days after their assignment row ended")
for person, hits in sorted(past.items()):
    days = sorted({day for day, *_ in hits})
    day, row, nxt, _ = hits[0]
    print(f"{person}: {len(days)} days {days[0]}..{days[-1]} on row {row['id']} (ended {row['valid_to']}, next row from {nxt}, {row['pay_type']})")
    for day, row, _, location in hits:
        if location.split("/")[-1].startswith("salaried.py"):
            excess += Fraction(row["monthly_salary"], 30)
print(f"salary paid for those days: {float(excess) / 100:,.2f}")
