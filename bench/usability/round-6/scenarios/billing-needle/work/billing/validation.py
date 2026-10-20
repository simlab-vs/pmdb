"""Pre-dispatch checks: bills held back for review before they are sent.

A bill is an exception when its consumption is implausible for the account
(far above or below its annual estimate, scaled to the billed days and the
season), when it is very large, or when its amounts don't add up.  The
exceptions go to the billing operations team; they are still issued.
"""

import csv
import logging
from typing import NamedTuple

from . import estimate, periods

log = logging.getLogger(__name__)

HIGH_FACTOR = 3.0
LOW_FACTOR = 0.2
LARGE_BILL_GBP = {"domestic": 750.0, "business": 25000.0}


class Exception_(NamedTuple):
    account: str
    code: str
    detail: str


def expected_kwh(account, period, days):
    """The consumption the annual estimate predicts for ``days`` of ``period``."""
    if account.eac <= 0:
        return None
    month = int(period.label[5:7])
    return account.eac / 365 * estimate.seasonal_factor(account.segment, month) * days


def consumption_checks(account, bill, period):
    found = []
    expected = expected_kwh(account, period, bill["days"])
    if expected is None or bill["basis"] != "actual":
        return found
    if bill["kwh"] > HIGH_FACTOR * expected:
        found.append(Exception_(account.account, "HIGH", f"{bill['kwh']:.1f} kWh, expected about {expected:.0f}"))
    elif bill["kwh"] < LOW_FACTOR * expected:
        found.append(Exception_(account.account, "LOW", f"{bill['kwh']:.1f} kWh, expected about {expected:.0f}"))
    return found


def amount_checks(account, bill):
    found = []
    lines_total = round(sum(line["amount"] for line in bill["lines"]), 2)
    if abs(lines_total - bill["net"]) > 0.005:
        found.append(Exception_(account.account, "SUM", f"lines {lines_total:.2f} != net {bill['net']:.2f}"))
    if abs(round(bill["net"] + bill["vat"], 2) - bill["gross"]) > 0.005:
        found.append(Exception_(account.account, "VAT", f"net + VAT != gross {bill['gross']:.2f}"))
    limit = LARGE_BILL_GBP.get(account.segment, LARGE_BILL_GBP["domestic"])
    if bill["gross"] > limit:
        found.append(Exception_(account.account, "LARGE", f"gross {bill['gross']:.2f} GBP"))
    if bill["gross"] < 0:
        found.append(Exception_(account.account, "CREDIT", f"gross {bill['gross']:.2f} GBP"))
    return found


def period_checks(account, bill, period):
    days = periods.overlap_days(period, account.move_in, account.move_out)
    if days != bill["days"]:
        return [Exception_(account.account, "DAYS", f"billed {bill['days']} days, supplied {days}")]
    return []


def review(bills, accounts, period):
    """Exceptions found in ``bills``, in account order."""
    found = []
    for bill in bills:
        account = accounts[bill["account"]]
        found.extend(consumption_checks(account, bill, period))
        found.extend(amount_checks(account, bill))
        found.extend(period_checks(account, bill, period))
    by_code = {}
    for item in found:
        by_code[item.code] = by_code.get(item.code, 0) + 1
    if found:
        log.info("review: %d exception(s): %s", len(found),
                 ", ".join(f"{code} {count}" for code, count in sorted(by_code.items())))
    return found


def write_exceptions(found, path):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["account", "code", "detail"])
        for item in found:
            writer.writerow(item)
