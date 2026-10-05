"""Outputs of a billing run: the bill register (CSV) and the run summary."""

import csv
from collections import Counter
from decimal import Decimal

BILL_COLUMNS = ("account", "name", "tariff", "basis", "days", "kwh", "net", "vat", "gross")


def write_bills(bills, path):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(BILL_COLUMNS)
        for bill in bills:
            row = dict(bill, kwh=f"{bill['kwh']:.3f}", net=f"{bill['net']:.2f}",
                       vat=f"{bill['vat']:.2f}", gross=f"{bill['gross']:.2f}")
            writer.writerow([row[column] for column in BILL_COLUMNS])


def _total(values):
    return sum((Decimal(str(value)) for value in values), Decimal(0))


def summarize(bills, period):
    actual = [bill for bill in bills if bill["basis"] == "actual"]
    estimated = [bill for bill in bills if bill["basis"] == "estimated"]
    return {
        "period": period.label,
        "bills": len(bills),
        "actual_bills": len(actual),
        "estimated_bills": len(estimated),
        "metered_kwh": _total(bill["kwh"] for bill in actual),
        "estimated_kwh": _total(bill["kwh"] for bill in estimated),
        "net": _total(bill["net"] for bill in bills),
        "vat": _total(bill["vat"] for bill in bills),
        "gross": _total(bill["gross"] for bill in bills),
        "by_tariff": dict(sorted(Counter(bill["tariff"] for bill in bills).items())),
    }


def format_summary(summary):
    lines = [
        f"Billing run {summary['period']}",
        f"  bills issued          {summary['bills']:>14,}",
        f"    on actual readings  {summary['actual_bills']:>14,}",
        f"    on estimates        {summary['estimated_bills']:>14,}",
        f"  metered consumption   {summary['metered_kwh']:>14,.1f} kWh",
        f"  estimated consumption {summary['estimated_kwh']:>14,.1f} kWh",
        f"  net amount            {summary['net']:>14,.2f} GBP",
        f"  VAT                   {summary['vat']:>14,.2f} GBP",
        f"  gross amount          {summary['gross']:>14,.2f} GBP",
        "  bills by tariff:",
    ]
    lines.extend(f"    {code:<20}{count:>14,}" for code, count in summary["by_tariff"].items())
    return "\n".join(lines)


def write_summary(summary, path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(format_summary(summary) + "\n")
