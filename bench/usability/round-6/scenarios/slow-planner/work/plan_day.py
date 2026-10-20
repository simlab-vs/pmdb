#!/usr/bin/env python3
"""Plans the delivery routes of one day.

    python3 plan_day.py data/orders_2026-09-28.json --fleet data/fleet.json -o out/
"""

import argparse
import logging
import sys
import time

from routeplan.construct import initial_plan
from routeplan.instance import load_day
from routeplan.report import check_plan, write_outputs
from routeplan.search import improve

log = logging.getLogger("plan_day")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("orders", help="the day's orders (JSON)")
    parser.add_argument("--fleet", required=True, help="the fleet (JSON)")
    parser.add_argument("-o", "--out", default="out", help="output directory")
    parser.add_argument("--rounds", type=int, default=60, help="ruin-and-recreate rounds")
    parser.add_argument("--seed", type=int, default=1, help="seed of the search")
    parser.add_argument("--neighbours", type=int, default=48,
                        help="nearest neighbours considered per stop")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    started = time.monotonic()
    inst = load_day(args.orders, args.fleet, args.neighbours)
    plan = initial_plan(inst)
    plan = improve(plan, args.rounds, args.seed)
    rows, problems = check_plan(inst, plan)
    text = write_outputs(inst, plan, rows, problems, args.out)
    sys.stdout.write(text)
    log.info("done in %.0f s", time.monotonic() - started)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
