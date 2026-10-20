"""Reading a quote run's inputs."""

import csv
import json
import os


class InputError(ValueError):
    """An input file is malformed."""


def load_customers(path):
    """Read ``customers.csv`` into a dict from customer id to a row dict."""
    customers = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row["id"].strip()
            if cid in customers:
                raise InputError(f"{path}: customer {cid} listed twice")
            customers[cid] = {
                "id": cid,
                "name": row["name"].strip(),
                "city": row["city"].strip(),
                "country": row["country"].strip().upper(),
                "tier": row["tier"].strip().lower(),
                "vat_id": row.get("vat_id", "").strip(),
            }
    return customers


def load_orders(path):
    """Read ``orders.jsonl``: one order per line, in the order received."""
    orders = []
    seen = set()
    with open(path, encoding="utf-8") as f:
        for number, text in enumerate(f, 1):
            text = text.strip()
            if not text:
                continue
            try:
                order = json.loads(text)
            except json.JSONDecodeError as exc:
                raise InputError(f"{path}:{number}: {exc}") from None
            for field in ("id", "customer", "lines"):
                if field not in order:
                    raise InputError(f"{path}:{number}: missing {field!r}")
            if order["id"] in seen:
                raise InputError(f"{path}:{number}: duplicate order {order['id']}")
            seen.add(order["id"])
            orders.append(order)
    return orders


def input_paths(data_dir):
    """The paths of a run's inputs inside ``data_dir``."""
    return {
        "regions": os.path.join(data_dir, "regions.json"),
        "catalog": os.path.join(data_dir, "catalog"),
        "offers": os.path.join(data_dir, "offers.json"),
        "customers": os.path.join(data_dir, "customers.csv"),
        "orders": os.path.join(data_dir, "orders.jsonl"),
    }
