"""The billing cycle: from merged readings to one bill per active account."""

import logging

from . import bills, estimate, meters, periods
from .accounts import canonical_id

log = logging.getLogger(__name__)


def account_batches(readings, identifiers):
    """Group the merged reading stream into (account, readings) batches.

    ``identifiers`` maps the canonical form of every identifier the meter
    operators use to the register's account identifier.
    """
    current = None
    batch = []
    unknown = set()
    for reading in readings:
        account_id = identifiers.get(canonical_id(reading.account))
        if account_id is None:
            if reading.account not in unknown:
                log.warning("readings for unknown account %r skipped", reading.account)
                unknown.add(reading.account)
            continue
        if account_id != current:
            if batch:
                yield current, batch
            current, batch = account_id, []
        batch.append(reading)
    if batch:
        yield current, batch


def billing_days(account, period):
    return periods.overlap_days(period, account.move_in, account.move_out)


def settle_account(account, readings, tariffs, exchanges, period):
    """The bill of one account, on actual readings when there are enough."""
    days = billing_days(account, period)
    kwh = meters.account_consumption(account.account, readings, exchanges)
    basis = "actual"
    if kwh is None:
        kwh = estimate.estimate_consumption(account, period, days)
        basis = "estimated"
    return bills.compose_bill(account, tariffs[account.tariff], kwh, basis, days, period)


def run_cycle(readings, register, tariffs, exchanges, period):
    """Bills of every account active in ``period``, by account."""
    issued = {}
    inactive = 0
    accounts = register.accounts()
    for account_id, batch in account_batches(readings, register.identifiers()):
        account = accounts[account_id]
        if billing_days(account, period) == 0:
            inactive += 1
            continue
        issued[account_id] = settle_account(account, batch, tariffs, exchanges.get(account_id, []), period)
    for account in register.active(period):
        if account.account not in issued:
            issued[account.account] = settle_account(
                account, [], tariffs, exchanges.get(account.account, []), period
            )
    if inactive:
        log.warning("%d account(s) with readings but no supply in %s", inactive, period.label)
    estimated = sum(1 for bill in issued.values() if bill["basis"] == "estimated")
    log.info("cycle %s: %d bills, %d on estimates", period.label, len(issued), estimated)
    return [issued[account_id] for account_id in sorted(issued)]
