"""Customer master data, enterprise contracts and plan changes."""

import csv
import json
from operator import itemgetter
from pathlib import Path

from .util import group_by, ranked


class CustomerDataError(ValueError):
    pass


def _flag(value):
    return value.strip().lower() in ("1", "true", "yes", "y")


def load_customers(path, plans):
    """Read ``customers.csv`` into a list of dicts, one per billable customer."""
    customers = []
    seen = set()
    with open(path, newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            customer_id = row["id"].strip()
            if customer_id in seen:
                raise CustomerDataError(f"customers.csv:{line}: duplicate customer {customer_id}")
            seen.add(customer_id)
            if row["plan"] not in plans:
                raise CustomerDataError(f"customers.csv:{line}: unknown plan {row['plan']!r}")
            customers.append({
                "id": customer_id,
                "name": row["name"].strip(),
                "country": row["country"].strip().upper(),
                "currency": row["currency"].strip().upper(),
                "plan": row["plan"],
                "segment": row["segment"].strip() or "self_serve",
                "vat_id": row["vat_id"].strip(),
                "discount_pct": float(row["discount_pct"] or 0),
                "active": not _flag(row.get("suspended", "")),
            })
    return customers


def load_contracts(path, period):
    """Read ``contracts.json`` into ``{customer id: [contract]}``, keeping the
    contracts in force during the period."""
    path = Path(path)
    if not path.exists():
        return {}
    contracts = {}
    for raw in json.loads(path.read_text()):
        if raw["end"] < period.start or raw["start"] > period.end:
            continue
        contract = {
            "id": raw["id"],
            "customer": raw["customer"],
            "metric": raw["metric"],
            "committed_units": int(raw["committed_units"]),
            "discount_pct": float(raw.get("discount_pct", 0)),
            "start": raw["start"],
            "end": raw["end"],
        }
        contracts.setdefault(contract["customer"], []).append(contract)
    return contracts


def load_plan_changes(path, period):
    """Read ``plan_changes.csv`` into ``{customer id: [change]}`` sorted by date,
    keeping the changes effective during the period."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if period.start <= row["effective"] <= period.end]
    changes = group_by(
        ({"customer": row["customer"], "effective": row["effective"],
          "from_plan": row["from_plan"], "to_plan": row["to_plan"]} for row in rows),
        key=itemgetter("customer"),
    )
    return {customer: ranked(history, key=itemgetter("effective")) for customer, history in changes.items()}


def billing_order(customers):
    """Customers are invoiced in the order of their IDs, so invoice numbers are stable."""
    return ranked([c for c in customers if c["active"]], key=itemgetter("id"))
