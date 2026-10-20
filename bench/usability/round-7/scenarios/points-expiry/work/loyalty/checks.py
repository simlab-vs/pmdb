"""Consistency checks run before the reports are written."""

import logging

from . import store
from .models import LEDGER_EXPIRE, LEDGER_FORFEIT

log = logging.getLogger(__name__)


class CheckFailed(RuntimeError):
    pass


def check_posting(conn, business_date):
    left = store.pending_count(conn, business_date)
    if left:
        raise CheckFailed(f"{left} activity records of {business_date} are still pending")


def check_lots(conn):
    bad = store.lot_violations(conn)
    if bad:
        raise CheckFailed(f"{bad} lots have a negative balance or more points left than earned")


def check_expiry_booked(conn, business_date, totals):
    booked = -store.ledger_total(conn, business_date, LEDGER_EXPIRE)
    if booked != totals.expired_points:
        raise CheckFailed(f"ledger has {booked} expired points for {business_date}, run counted "
                          f"{totals.expired_points}")
    forfeited = -store.ledger_total(conn, business_date, LEDGER_FORFEIT)
    if forfeited != totals.forfeited:
        raise CheckFailed(f"ledger has {forfeited} forfeited points for {business_date}, run counted "
                          f"{totals.forfeited}")


def check_statements(sent, members, closed):
    if sent != members - closed:
        raise CheckFailed(f"pushed {sent} statements for {members - closed} open accounts")
