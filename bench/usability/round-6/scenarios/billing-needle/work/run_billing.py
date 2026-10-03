#!/usr/bin/env python3
"""Run the monthly billing cycle.

    python3 run_billing.py --period 2026-09 --data data --out out

Reads the customer register, the tariffs, the meter events and the meter
operators' reading feeds from ``--data``, and writes the bill register
``bills_<period>.csv``, the bills held for review ``exceptions_<period>.csv``
and ``summary_<period>.txt`` to ``--out``.
"""

import argparse
import logging
import sys
from pathlib import Path

from billing import accounts, cycle, feeds, meters, periods, report, tariffs, validation


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Monthly electricity billing run.")
    parser.add_argument("--period", required=True, help="billing month, YYYY-MM")
    parser.add_argument("--data", default="data", type=Path, help="input directory")
    parser.add_argument("--out", default="out", type=Path, help="output directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debugging details")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    period = periods.parse_period(args.period)
    register = accounts.load_register(args.data / "customers.csv")
    plan = tariffs.load_tariffs(args.data / "tariffs.json")
    exchanges = meters.load_exchanges(args.data / "meter_events.csv", register)
    readings = feeds.load_all(args.data / "feeds", period)

    bills = cycle.run_cycle(readings, register, plan, exchanges, period)

    args.out.mkdir(parents=True, exist_ok=True)
    report.write_bills(bills, args.out / f"bills_{period.label}.csv")
    exceptions = validation.review(bills, register.accounts(), period)
    validation.write_exceptions(exceptions, args.out / f"exceptions_{period.label}.csv")
    summary = report.summarize(bills, period)
    report.write_summary(summary, args.out / f"summary_{period.label}.txt")
    print(report.format_summary(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
