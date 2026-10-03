"""Run reports: ``nightly-<date>.json`` (for the finance data import) and a
text version; at month end also ``liability-<month>.txt`` for the controller."""

import json
import logging
import os

from . import clock, dates

log = logging.getLogger(__name__)


def fmt(n):
    return f"{n:,}"


def text_report(report):
    posting, expiry, liability = report["posting"], report["expiry"], report["liability"]
    lines = [
        f"{report['programme']}: nightly points run",
        f"Business date: {report['business_date']} ({report['mode']})",
        f"Generated: {report['generated_at']}",
        "",
        "Posting",
        f"  earn records      {posting['earn']:>10}   points {fmt(posting['earn_points']):>14}",
        f"  burn records      {posting['burn']:>10}   points {fmt(posting['burn_points']):>14}",
        f"  adjustments       {posting['adjust']:>10}   points {fmt(posting['adjust_points']):>14}",
        f"  rejected          {posting['rejected']:>10}",
    ]
    if report["mode"] == "month-end":
        lines += [
            "",
            "Month end",
            f"  expired points                 {fmt(expiry['expired_points']):>14}",
        ]
        for source, points in expiry["expired_by_source"].items():
            lines.append(f"    {source:<26} {fmt(points):>14}")
        lines += [
            f"  members with expiry            {fmt(expiry['members_with_expiry']):>14}",
            f"  forfeited (closed accounts)    {fmt(expiry['forfeited_points']):>14}",
            f"  statements pushed              {fmt(report['statements']):>14}",
        ]
    lines += [
        "",
        "Liability",
        f"  outstanding points             {fmt(liability['outstanding_points']):>14}",
    ]
    for tier, points in liability["outstanding_by_tier"].items():
        lines.append(f"    {tier:<26} {fmt(points):>14}")
    lines += [
        f"  closed accounts (to forfeit)   {fmt(liability['closed_accounts_points']):>14}",
        f"  expiring {liability['expiring_next_month']['on']}          "
        f"{fmt(liability['expiring_next_month']['points']):>14}",
        f"  value (EUR, after breakage)    {liability['value_eur']:>14}",
    ]
    return "\n".join(lines) + "\n"


def write_reports(out_dir, report):
    os.makedirs(out_dir, exist_ok=True)
    day = report["business_date"]
    paths = [os.path.join(out_dir, f"nightly-{day}.json"), os.path.join(out_dir, f"nightly-{day}.txt")]
    with open(paths[0], "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    text = text_report(report)
    with open(paths[1], "w", encoding="utf-8") as handle:
        handle.write(text)
    if report["mode"] == "month-end":
        paths.append(os.path.join(out_dir, f"liability-{dates.month_key(day)}.txt"))
        with open(paths[2], "w", encoding="utf-8") as handle:
            handle.write(text)
    log.info("wrote %s", ", ".join(paths))
    return paths


def report_header(programme, business_date, mode):
    return {
        "programme": programme,
        "business_date": business_date,
        "mode": mode,
        "generated_at": clock.stamp(),
    }
