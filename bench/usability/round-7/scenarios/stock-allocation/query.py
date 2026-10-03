"""Aggregate the allocations with a negative pick (exported by query.pmdb)."""
import json
from collections import Counter

calls = [json.loads(line) for line in open("negative.jsonl")]
negative, topped_up, lines = Counter(), Counter(), Counter()
for call in calls:
    allocation = call["returned"]
    lines[allocation["channel"]] += 1
    for pick in allocation["picks"]:
        if pick["qty"] < 0:
            negative[pick["warehouse"]] -= pick["qty"]
        else:
            topped_up[pick["warehouse"]] += pick["qty"]
print(f"{len(calls)} lines with a negative pick, by channel: {dict(sorted(lines.items()))}")
print(f"negative units by warehouse: {dict(sorted(negative.items()))}")
print(f"units picked elsewhere on those lines: {dict(sorted(topped_up.items()))}")
