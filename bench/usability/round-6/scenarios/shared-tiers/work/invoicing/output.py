"""Writing the run's invoices and its summary."""

import csv
import json
from collections import defaultdict
from operator import itemgetter
from pathlib import Path

from .money import sum_amounts
from .util import ranked


def write_invoices(out_dir, invoices):
    """One JSON document per line in ``invoices.jsonl``, in invoice-number order."""
    path = Path(out_dir) / "invoices.jsonl"
    with open(path, "w") as handle:
        for invoice in sorted(invoices, key=lambda i: i["number"]):
            handle.write(json.dumps(invoice, sort_keys=True) + "\n")
    return path


def write_lines_csv(out_dir, invoices):
    """A flat CSV of every invoice line, for the accounting import."""
    path = Path(out_dir) / "invoice_lines.csv"
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["invoice", "customer", "currency", "code", "quantity", "amount"])
        for invoice in invoices:
            for line in invoice["lines"]:
                writer.writerow([invoice["number"], invoice["customer"], invoice["currency"],
                                 line["code"], line["quantity"], f"{line['amount']:.2f}"])
    return path


def summarize(invoices):
    """Totals per currency and per plan, as printed at the end of the run."""
    per_currency = defaultdict(list)
    per_plan = defaultdict(lambda: defaultdict(list))
    for invoice in invoices:
        per_currency[invoice["currency"]].append(invoice["total"])
        per_plan[invoice["plan"]][invoice["currency"]].append(invoice["subtotal"])
    largest = ranked([(i["number"], i["name"], i["subtotal"]) for i in invoices if i["currency"] == "EUR"],
                     key=itemgetter(2), descending=True)[:5]
    return {
        "invoices": len(invoices),
        "largest_eur": largest,
        "totals": {cur: sum_amounts(v) for cur, v in sorted(per_currency.items())},
        "net_by_plan": {
            plan: {cur: sum_amounts(v) for cur, v in sorted(by_cur.items())}
            for plan, by_cur in sorted(per_plan.items())
        },
    }


def write_summary(out_dir, summary):
    path = Path(out_dir) / "summary.txt"
    rows = [f"Invoices: {summary['invoices']}"]
    for currency, total in summary["totals"].items():
        rows.append(f"Total {currency}: {total:,.2f}")
    for plan, by_currency in summary["net_by_plan"].items():
        for currency, net in by_currency.items():
            rows.append(f"Net {plan} {currency}: {net:,.2f}")
    rows.append("Largest EUR invoices:")
    for number, name, subtotal in summary["largest_eur"]:
        rows.append(f"  {number} {name}: {subtotal:,.2f}")
    path.write_text("\n".join(rows) + "\n")
    return path
