#!/usr/bin/env python3
"""Monthly payroll run.

Usage:
    python3 run_payroll.py --hr-export HR.json --period YYYY-MM [--out DIR] [--bank-out DIR] [--log FILE]
"""

import argparse
import logging
import sys
from pathlib import Path

from payroll import __version__
from payroll import hourly, payslip as payslip_module
from payroll.bankfile import write_bank_file
from payroll.checks import CheckFailed, check_run
from payroll.hrexport import ExportError, read_export
from payroll.models import HOURLY, SALARIED
from payroll.money import fmt
from payroll.payslip import compute_payslips
from payroll.periods import PeriodError, parse_period
from payroll.register import Register
from payroll.report import write_report
from payroll.settings import load_rules

HERE = Path(__file__).resolve().parent
log = logging.getLogger("payroll")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hr-export", required=True, help="the HR system's export for the period (JSON)")
    parser.add_argument("--period", required=True, help="pay period, YYYY-MM")
    parser.add_argument("--out", help="register directory (default from the config)")
    parser.add_argument("--bank-out", help="credit-transfer directory (default from the config)")
    parser.add_argument("--config", default=str(HERE / "config" / "payroll.toml"))
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


def run(args):
    rules = load_rules(args.config)
    period = parse_period(args.period)
    persons, shifts, exported_period = read_export(args.hr_export)
    if exported_period and exported_period != period.month:
        raise ExportError(f"export is for {exported_period}, not {period.month}")

    register = Register(rules.cost_centres)
    payslips = []
    for person, payslip in compute_payslips(persons, shifts, period, rules):
        register.add(payslip)
        payslips.append((person, payslip))

    stats = payslip_module.STATS
    kinds = {SALARIED: 0, HOURLY: 0}
    for _, payslip in payslips:
        kinds[payslip.pay_type] += 1
    log.info(
        "%d payslips (%d salaried, %d hourly, %d for part of the month); %d persons not employed in %s, %d rejected",
        len(payslips),
        kinds[SALARIED],
        kinds[HOURLY],
        stats["part-month"],
        stats["not employed"],
        period.month,
        stats["rejected"],
    )
    log.info(
        "timesheets: %d h worked, %d h at night, %d h overtime; %d paid absence days; %d unpaid leave days",
        stats["worked minutes"] // 60,
        stats["night minutes"] // 60,
        stats["overtime minutes"] // 60,
        stats["paid absence days"],
        stats["unpaid leave days"],
    )
    for reason, count in sorted(hourly.STATS.items()):
        log.info("%d timesheet entries ignored: %s", count, reason)

    check_run(payslips, register)
    out_dir = args.out or str(HERE / rules.report_dir)
    totals = write_report(out_dir, period, rules, register)
    for code, row, _ in register.by_cost_centre():
        log.info("%s gross %s net %s", code, fmt(row["gross"]), fmt(row["net"]))
    write_bank_file(args.bank_out or rules.bank_dir, period, rules, payslips)
    log.info("total gross %s EUR, net %s EUR", fmt(totals["gross"]), fmt(totals["net"]))


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log)
    log.info("payroll %s for %s", __version__, args.period)
    try:
        run(args)
    except (CheckFailed, ExportError, PeriodError) as exc:
        log.error("payroll run failed: %s", exc)
        return 2
    log.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
