"""Which dropped 're-sends' repeat no clearing that was posted? (run after query.pmdb, in the same directory)"""
import json
from collections import Counter
from decimal import Decimal


def messages(path):
    return [json.loads(line)["positional"][0] for line in open(path)]


posted = {m["data"]["network_ref"]: m for m in messages("posted.jsonl")}
dropped = messages("dropped.jsonl")
lost = list({m["data"]["network_ref"]: m for m in dropped if m["data"]["network_ref"] not in posted}.values())
total = sum(Decimal(m["data"]["billing_amount"]) for m in lost)
repeats = sum(1 for m in dropped if m["data"]["network_ref"] in posted)
print(f"dropped clearings: {len(dropped)}; repeating a posted network_ref: {repeats}; network_refs never posted: {len(lost)}, total {total}")
print("never posted, by MCC:", dict(Counter(m["data"]["merchant"]["mcc"] for m in lost).most_common()))
print("never posted, with an auth_code:", sum(1 for m in lost if m["data"].get("auth_code")))
example = lost[0]["data"]
twin = next(m["data"] for m in posted.values()
            if m["data"]["card"] == example["card"] and m["data"]["amount"] == example["amount"]
            and m["data"]["merchant"]["id"] == example["merchant"]["id"]
            and m["data"]["transaction_time"] == example["transaction_time"])
for label, d in (("posted ", twin), ("dropped", example)):
    print(label, d["card"], d["merchant"]["name"], d["amount"], d["transaction_time"], "network_ref", d["network_ref"])
