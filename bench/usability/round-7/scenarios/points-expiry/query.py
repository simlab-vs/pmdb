"""Aggregate query.pmdb's exports (run in the directory pmdb exported to)."""
import collections
import json

cutoffs = collections.Counter()
for line in open("cutoffs.jsonl"):
    call = json.loads(line)
    _, source, on = call["positional"]
    cutoffs[(on, source, call["returned"])] += 1
print("cutoff_for(source, on) -> cutoff: calls")
for (on, source, cutoff), n in sorted(cutoffs.items()):
    print(f"  {on} {source} -> {cutoff}: {n}")

expired = collections.Counter()
for line in open("due.jsonl"):
    call = json.loads(line)
    for lot in call["returned"]:
        expired[(lot["earned_on"][:7], lot["source"])] += lot["remaining"]
print("expired points by earning month and source")
for (month, source), points in sorted(expired.items()):
    print(f"  {month} {source}: {points}")
print(f"  total: {sum(expired.values())}")
