#!/usr/bin/env python3
"""Nightly points job of Northwind Rewards.

Usage:
    python3 nightly.py --db POINTS.db [--out DIR] [--log FILE] [--force]

Posts the day's earn/burn activity; on the last day of a month also books
the month's expiry and forfeiture and pushes the members' monthly
statements to the CRM. Writes the run report and the points liability.
"""

import argparse
import logging
import sys
from pathlib import Path

from loyalty import __version__, audit, checks, clock, dates, expiry, liability, posting, statements, store
from loyalty.crm import CrmClient, CrmError
from loyalty.policy import ExpiryPolicy
from loyalty.report import report_header, write_reports
from loyalty.settings import load_settings

HERE = Path(__file__).resolve().parent
log = logging.getLogger("loyalty")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="points database (SQLite)")
    parser.add_argument("--out", help="report directory (default from settings)")
    parser.add_argument("--config", default=str(HERE / "config" / "loyalty.toml"))
    parser.add_argument("--log", help="also append the log to this file")
    parser.add_argument("--force", action="store_true", help="run even if today's run already finished")
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


def month_end_stage(conn, members, policy, business_date, settings):
    """Expire and forfeit, batch by batch, and push each batch's statements."""
    totals = expiry.ExpiryTotals()
    crm = CrmClient(settings.crm_endpoint, settings.crm_timeout_s, settings.crm_retries)
    batches = list(expiry.batched(members, settings.batch_size))
    log.info("month end: expiry and statements for %d members in %d batches", len(members), len(batches))
    pushed = 0
    for number, batch in enumerate(batches, 1):
        expiry.expire_batch(conn, batch, policy, business_date, totals)
        items = statements.statements_for(conn, batch, policy, business_date)
        crm.push_all(items)
        pushed += len(items)
        if number % 4 == 0 or number == len(batches):
            log.info("batch %d/%d done: %d members, %d statements pushed", number, len(batches),
                     min(number * settings.batch_size, len(members)), pushed)
    if crm.retried:
        log.info("CRM: %d requests retried", crm.retried)
    log.info(
        "expired %s points (%s) of %d members; %d platinum members exempt",
        f"{totals.expired_points:,}",
        ", ".join(f"{source} {points:,}" for source, points in sorted(totals.expired.items())) or "none",
        totals.members_expired,
        totals.members_exempt,
    )
    log.info("forfeited %s points of %d closed accounts", f"{totals.forfeited:,}", totals.members_forfeited)
    checks.check_expiry_booked(conn, business_date, totals)
    return totals, pushed


def run(args):
    settings = load_settings(args.config)
    if settings.timezone != clock.ZONE_NAME:
        raise SystemExit(f"configured time zone {settings.timezone} is not {clock.ZONE_NAME}")
    started = clock.stamp()
    business_date = clock.today()
    mode = "month-end" if dates.is_month_end(business_date) else "daily"
    log.info("business date %s (%s run)", business_date, mode)

    conn = store.connect(args.db)
    if store.previous_run(conn, business_date) and not args.force:
        log.warning("the run of %s already finished; use --force to run again", business_date)
        return 3
    run_id = store.start_run(conn, business_date, started, mode)
    audit.begin(run_id)
    policy = ExpiryPolicy(settings.expiry_months, settings.exempt_tiers)

    members = store.all_members(conn)
    by_id = {member.id: member for member in members}
    closed = sum(1 for member in members if policy.forfeits(member))
    log.info("%d members (%d closed accounts)", len(members), closed)

    log.info("posting %d activity records of %s", store.pending_count(conn, business_date), business_date)
    posted = posting.post_day(conn, business_date, by_id, policy, settings.tier_multipliers)
    log.info(
        "posted %d earn (%s points), %d burn (%s points), %d adjustments; %d rejected",
        posted["earn"], f"{posted['earn_points']:,}", posted["burn"], f"{posted['burn_points']:,}",
        posted["adjust"], posted["rejected"],
    )
    later = store.later_pending_count(conn, business_date)
    if later:
        log.info("%d records of later business dates left for their runs", later)
    checks.check_posting(conn, business_date)

    expiry_totals, pushed = expiry.ExpiryTotals(), 0
    if mode == "month-end":
        expiry_totals, pushed = month_end_stage(conn, members, policy, business_date, settings)
        checks.check_statements(pushed, len(members), closed)

    summary = liability.summarize(conn, business_date, policy, settings.point_value_eur, settings.breakage_rate)
    checks.check_lots(conn)
    log.info(
        "outstanding %s points, EUR %s after breakage; %s points expire on %s",
        f"{summary['outstanding_points']:,}", summary["value_eur"],
        f"{summary['expiring_next_month']['points']:,}", summary["expiring_next_month"]["on"],
    )

    report = report_header(settings.programme, business_date, mode)
    report["posting"] = {
        key: posted[key]
        for key in ("earn", "burn", "adjust", "rejected", "earn_points", "burn_points", "adjust_points")
    }
    report["expiry"] = expiry_totals.as_dict()
    report["statements"] = pushed
    report["liability"] = summary
    out_dir = args.out or str(HERE / settings.report_dir)
    write_reports(out_dir, report)
    store.finish_run(conn, run_id, clock.stamp(), "ok", f"{audit.bookings()} bookings")
    conn.close()
    return 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log)
    log.info("nightly points job %s", __version__)
    try:
        status = run(args)
    except (checks.CheckFailed, CrmError) as exc:
        log.error("run failed: %s", exc)
        return 2
    if status == 0:
        log.info("done")
    return status


if __name__ == "__main__":
    sys.exit(main())
