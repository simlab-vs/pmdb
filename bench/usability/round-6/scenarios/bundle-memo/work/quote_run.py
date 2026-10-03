"""Price the day's open orders.

Usage: python3 quote_run.py DATA_DIR --date YYYY-MM-DD --out OUT_DIR
"""

import argparse
import logging
import sys
import time

from quoting import engine
from quoting.catalog import load_catalog, price_list_count
from quoting.loader import input_paths, load_customers, load_orders
from quoting.offers import load_offers
from quoting.quote import quote_order
from quoting.regions import load_regions
from quoting.report import summarize, write_quotes, write_summary

log = logging.getLogger("quote_run")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_dir")
    parser.add_argument("--date", required=True, help="the day the quotes are valid")
    parser.add_argument("--out", default="out")
    parser.add_argument("--only", nargs="*", help="price only these order ids")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def run(args):
    paths = input_paths(args.data_dir)
    regions = load_regions(paths["regions"])
    load_catalog(paths["catalog"], regions)
    offers = load_offers(paths["offers"])
    customers = load_customers(paths["customers"])
    orders = load_orders(paths["orders"])
    if args.only:
        wanted = set(args.only)
        orders = [o for o in orders if o["id"] in wanted]
    log.info("%d orders, %d customers, %d offers, %d price lists",
             len(orders), len(customers), len(offers), price_list_count())
    engine.configure(offers)
    started = time.monotonic()
    quotes = [
        quote_order(order, customers.get(order["customer"]), regions, args.date)
        for order in orders
    ]
    log.info("priced %d orders in %.1f s", len(quotes), time.monotonic() - started)
    log.debug("%(searched)d sub-carts searched, %(reused)d reused", engine.stats)
    write_quotes(quotes, args.out)
    summary = summarize(quotes)
    write_summary(summary, args.date, args.out)
    rejected = sum(summary["rejected"].values())
    if rejected:
        log.warning("%d orders rejected, see %s/quotes.csv", rejected, args.out)
    return 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
