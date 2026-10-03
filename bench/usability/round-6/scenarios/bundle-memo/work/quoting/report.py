"""Writing a run's quotes and its summary."""

import csv
import os
from collections import defaultdict

from .money import display, format_amount

COLUMNS = (
    "id", "customer", "status", "region", "currency", "tier", "channel", "units",
    "list_price", "savings", "subtotal", "shipping", "vat", "total", "offers", "reason",
)
AMOUNTS = ("list_price", "savings", "subtotal", "shipping", "vat", "total")


def _row(quote):
    row = {c: quote.get(c, "") for c in COLUMNS}
    for column in AMOUNTS:
        if column in quote:
            row[column] = format_amount(quote[column])
    if quote["status"] == "ok":
        used = sorted({line["offer"] for line in quote["lines"] if line["offer"]})
        row["offers"] = " ".join(used)
    return row


def write_quotes(quotes, out_dir):
    """Write ``quotes.csv`` to ``out_dir``."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "quotes.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for quote in quotes:
            writer.writerow(_row(quote))


def summarize(quotes):
    """Totals of a run per currency and per region."""
    by_currency = defaultdict(lambda: {"quotes": 0, "total": 0, "savings": 0})
    by_region = defaultdict(int)
    rejected = defaultdict(int)
    offers = defaultdict(int)
    for quote in quotes:
        if quote["status"] != "ok":
            rejected[quote["reason"]] += 1
            continue
        entry = by_currency[quote["currency"]]
        entry["quotes"] += 1
        entry["total"] += quote["total"]
        entry["savings"] += quote["savings"]
        by_region[quote["region"]] += 1
        for line in quote["lines"]:
            if line["offer"]:
                offers[line["offer"]] += 1
    return {
        "by_currency": dict(by_currency),
        "by_region": dict(by_region),
        "rejected": dict(rejected),
        "offers": dict(offers),
    }


def write_summary(summary, date, out_dir):
    """Write ``summary.txt`` to ``out_dir``."""
    lines = [f"Quote run {date}", ""]
    for currency, entry in sorted(summary["by_currency"].items()):
        lines.append(
            f"{currency}: {entry['quotes']} quotes, total {display(entry['total'], currency)}, "
            f"savings {display(entry['savings'], currency)}"
        )
    lines.append("")
    lines.append("Quotes per region: " + ", ".join(
        f"{code} {n}" for code, n in sorted(summary["by_region"].items())))
    lines.append("Offers used: " + ", ".join(
        f"{oid} {n}" for oid, n in sorted(summary["offers"].items())))
    rejected = sum(summary["rejected"].values())
    lines.append(f"Rejected: {rejected}")
    for reason, n in sorted(summary["rejected"].items()):
        lines.append(f"  {n} x {reason}")
    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
