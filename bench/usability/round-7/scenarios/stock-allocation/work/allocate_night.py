#!/usr/bin/env python3
"""Nightly order allocation.

Usage:
    python3 allocate_night.py --orders OPEN-LINES.jsonl --date YYYY-MM-DD
        [--levels-file LEVELS.json] [--out DIR] [--reports DIR] [--log FILE]
"""

import argparse
import logging
import sys
from pathlib import Path

from alloc import __version__, allocator, catalog, inventory, ledger, policy, routing
from alloc.checks import CheckFailed, run_checks
from alloc.orders import load_lines
from alloc.picklists import write_pick_lists
from alloc.settings import load_settings
from alloc.summary import summarize, write_summary

HERE = Path(__file__).resolve().parent
log = logging.getLogger("alloc")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--orders", required=True, help="OMS export of open order lines (JSON Lines)")
    parser.add_argument("--date", required=True, help="allocation day, YYYY-MM-DD")
    parser.add_argument("--levels-file", help="read stock levels from a dump instead of the inventory service")
    parser.add_argument("--out", help="pick list directory (default from settings)")
    parser.add_argument("--reports", help="summary directory (default from settings)")
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


def run(args):
    settings = load_settings(args.config)
    catalog.load_catalog(HERE / settings.catalog_dir)
    levels = inventory.load_levels(settings, args.levels_file, catalog.stocked_skus())
    ledger.open_ledger(levels)
    routing.configure(settings)
    policy.configure(settings)

    lines = load_lines(args.orders, settings.express_first)
    allocations = allocator.allocate_all(lines)
    ship_complete = {line.order_id for line in lines if line.ship_complete}
    run_checks(allocations, ship_complete)

    out_dir = args.out or str(HERE / settings.out_dir)
    write_pick_lists(out_dir, args.date, settings.warehouses, allocations, settings.wave_size)
    summary = summarize(allocations, settings.warehouses)
    names = {code: spec.name for code, spec in settings.warehouses.items()}
    write_summary(args.reports or str(HERE / settings.report_dir), args.date, summary, names)
    for code, stats in summary["warehouses"].items():
        log.info("%s: %d orders, %d lines, %d units", names[code], stats["orders"], stats["lines"], stats["units"])
    reserved = ledger.reserved_by_warehouse()
    log.info("reserved this run: %s", ", ".join(f"{c} {reserved.get(c, 0)}" for c in settings.warehouses))


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log)
    log.info("order allocation %s for %s", __version__, args.date)
    try:
        run(args)
    except (CheckFailed, inventory.InventoryError, ledger.OverAllocation) as exc:
        log.error("allocation stopped: %s", exc)
        return 2
    log.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
