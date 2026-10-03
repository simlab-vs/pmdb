"""Command line entry point of the monthly invoicing run."""

import argparse
import logging
from pathlib import Path

from .catalog import billed_metrics, load_catalog
from .config import load_settings, parse_period
from .customers import billing_order, load_contracts, load_customers, load_plan_changes
from .fx import load_rates
from .invoice import RunContext, build_invoice
from .output import summarize, write_invoices, write_lines_csv, write_summary
from .usage import load_usage

log = logging.getLogger("invoicing")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Compute the monthly invoices.")
    parser.add_argument("data", type=Path, help="directory with the run's input files")
    parser.add_argument("--period", required=True, help="billing period, YYYY-MM")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def load_context(data, period_label):
    settings = load_settings(data / "settings.json")
    period = parse_period(period_label)
    plans = load_catalog(data / "plans.json")
    usage, skipped = load_usage(data / f"usage_{period.label}.csv", period, billed_metrics(plans))
    if skipped:
        log.info("skipped %d usage records outside the period or not billed", skipped)
    contracts = load_contracts(data / "contracts.json", period)
    changes = load_plan_changes(data / "plan_changes.csv", period)
    rates = load_rates(data / "fx.json", period, settings.base_currency)
    customers = load_customers(data / "customers.csv", plans)
    return RunContext(settings, period, plans, usage, contracts, changes, rates), customers


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")
    ctx, customers = load_context(args.data, args.period)
    args.out.mkdir(parents=True, exist_ok=True)
    invoices = []
    for customer in billing_order(customers):
        invoices.append(build_invoice(customer, ctx))
    write_invoices(args.out, invoices)
    write_lines_csv(args.out, invoices)
    summary = summarize(invoices)
    write_summary(args.out, summary)
    log.info("wrote %d invoices to %s", summary["invoices"], args.out)
    for currency, total in summary["totals"].items():
        log.info("total %s %s", currency, f"{total:,.2f}")
    return 0
