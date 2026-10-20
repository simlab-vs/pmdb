#!/usr/bin/env python3
"""Monthly payout reconciliation job.

Usage:
    python3 monthly_report.py --export EVENTS.jsonl[.gz] --month YYYY-MM [--out DIR]
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

from recon import __version__
from recon.checks import (
    CheckFailed,
    check_books,
    check_currencies,
    check_kinds,
    check_refund_parents,
)
from recon.fx import FxTable
from recon.ledger import Ledger
from recon.models import CHARGE, REFUND, DISPUTE
from recon.loader import load_export
from recon.money import fmt
from recon.providers import adapter_for
from recon.report import write_report
from recon.settings import load_settings
from recon.timeutil import month_window

HERE = Path(__file__).resolve().parent
log = logging.getLogger("recon")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", required=True, help="provider event export")
    parser.add_argument("--month", required=True, help="month to reconcile, YYYY-MM")
    parser.add_argument("--out", help="report directory (default from settings)")
    parser.add_argument("--config", default=str(HERE / "config" / "settings.toml"))
    parser.add_argument("--log", help="also append the log to this file")
    return parser.parse_args(argv)


def setup_logging(log_file):
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def normalize_all(events, fx):
    for event in events:
        normalize = adapter_for(event.provider)
        yield normalize(event, fx)


def run(args):
    settings = load_settings(args.config)
    start, end = month_window(args.month)
    fx_path = HERE / settings.fx_dir / f"{args.month}.csv"
    fx = FxTable.load(fx_path, base=settings.settlement_currency)

    events = load_export(args.export, settings.providers, start, end)
    ledger = Ledger(settings.providers, settings.ignored_statuses)
    kinds, foreign, earlier = {}, Counter(), Counter()
    charge_refs = set()
    for txn in normalize_all(events, fx):
        kinds.setdefault(txn.provider, Counter())[txn.kind] += 1
        if txn.currency != settings.settlement_currency:
            foreign[txn.currency] += 1
        if txn.kind == CHARGE:
            charge_refs.add((txn.provider, txn.ref))
        elif txn.kind in (REFUND, DISPUTE) and (txn.provider, txn.parent) not in charge_refs:
            earlier[txn.provider] += 1
        ledger.apply(txn)
    check_kinds(kinds)
    check_currencies(foreign, settings.settlement_currency)
    check_refund_parents(earlier)
    ledger.log_summary()
    check_books(ledger)

    out_dir = args.out or str(HERE / settings.report_dir)
    rows = write_report(out_dir, args.month, settings.settlement_currency, ledger)
    for provider, values in rows:
        log.info("%s net payout %s %s", provider, fmt(values["net"]), settings.settlement_currency)
    if fx.fallbacks:
        log.info("%d FX lookups used an earlier day's rate", fx.fallbacks)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log)
    log.info("payout reconciliation %s for %s", __version__, args.month)
    try:
        run(args)
    except CheckFailed as exc:
        log.error("check failed: %s", exc)
        return 2
    log.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
