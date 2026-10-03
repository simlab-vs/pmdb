#!/usr/bin/env python3
"""Daily card ledger run: drain the card-events queue and write the end-of-day files.

Usage:
    python3 run_ledger.py --business-date YYYY-MM-DD [--spool DUMP] [--out DIR] [--log FILE]
"""

import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from ledger import __version__, consumer, dedup, holds, parking, postings
from ledger.checks import CheckFailed, check_balanced, check_overdrawn, check_stats
from ledger.dedup import NEW
from ledger.messages import MessageError, parse_message
from ledger.money import fmt
from ledger.queue_client import QueueError, drain, open_queue
from ledger.report import write_balances, write_summary
from ledger.settings import load_settings

HERE = Path(__file__).resolve().parent
log = logging.getLogger("cardledger")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--business-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--spool", default=os.environ.get("CARDLEDGER_SPOOL"),
                        help="read a queue dump instead of the queue (tests, replays)")
    parser.add_argument("--out", help="output directory (default from settings)")
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
    dedup.reset()
    consumer.configure(settings)
    queue = open_queue(settings.queue_url, args.spool)
    stats = Counter()
    try:
        for batch in drain(queue, settings.receive_batch, stats):
            for raw in batch:
                try:
                    message = parse_message(raw)
                except MessageError as exc:
                    stats["unreadable"] += 1
                    log.warning("%s", exc)
                    continue
                if dedup.classify(message) == NEW:
                    stats[consumer.handle(message)] += 1
    finally:
        queue.close()
    log.info("received %d messages in %d batches from %s", stats["received"], stats["batches"], queue.name)
    check_stats(dedup.stats, stats["received"] - stats["unreadable"])
    log.info(
        "dropped %d queue redeliveries and %d processor re-sends",
        dedup.stats["redelivery"], dedup.stats["resend"],
    )
    events = consumer.stats
    log.info(
        "applied %d authorizations, %d reversals, %d clearings (%d offline), %d refunds, %d top-ups",
        events["authorization"], events["authorization.reversal"], events["clearing"],
        events["offline"], events["refund"], events["topup"],
    )
    if events["other_programme"]:
        log.info("skipped %d notifications of other programmes", events["other_programme"])
    late = consumer.finish()
    log.info(
        "parked %d events ahead of their authorization, %d matched later; "
        "%d late presentments posted without a hold, %d reversals of unknown authorizations",
        parking.stats["parked"], parking.stats["released"], late["clearing"], late["authorization.reversal"],
    )

    check_balanced()
    check_overdrawn()

    totals = postings.totals()
    counts = postings.counts()
    log.info(
        "fees: %d FX fees %s, %d ATM fees %s",
        counts["fx_fee"], fmt(totals["fx_fee"]), counts["atm_fee"], fmt(totals["atm_fee"]),
    )
    log.info("holds: %d open, %s held at close", holds.open_count(), fmt(sum(holds.outstanding().values())))

    out_dir = Path(args.out or HERE / settings.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_stats = {
        "received": stats["received"],
        "redeliveries": dedup.stats["redelivery"],
        "resends": dedup.stats["resend"],
        "parked": parking.stats["parked"],
    }
    balances = write_balances(out_dir, args.business_date, settings.currency)
    json_path, txt_path = write_summary(out_dir, args.business_date, settings, run_stats)
    log.info("wrote %s, %s and %s", balances, json_path, txt_path)
    log.info(
        "clearings %s, refunds %s, top-ups %s, net movement %s %s over %d cards",
        fmt(totals["clearing"]), fmt(totals["refund"]), fmt(totals["topup"]),
        fmt(sum(postings.movement().values())), settings.currency, len(postings.cards()),
    )


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log)
    log.info("card ledger %s for business date %s", __version__, args.business_date)
    try:
        run(args)
    except (CheckFailed, QueueError) as exc:
        log.error("%s", exc)
        return 2
    log.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
