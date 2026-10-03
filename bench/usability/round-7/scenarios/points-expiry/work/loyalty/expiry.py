"""Month-end expiry and forfeiture of points.

Members are processed in batches (``[expiry] batch_size``); each batch is
one database transaction, so an interrupted run can be resumed without
booking a lot twice: lots already closed are no longer open.
"""

import logging
from collections import Counter
from itertools import islice

from . import audit, store
from .models import LEDGER_EXPIRE, LEDGER_FORFEIT

log = logging.getLogger(__name__)


def batched(items, size):
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def forfeit_member(conn, member, lots, posted_on):
    forfeited = 0
    for lot in lots:
        store.close_lot(conn, lot.id, posted_on)
        store.insert_ledger(conn, member.id, posted_on, LEDGER_FORFEIT, -lot.remaining, lot.id, audit.stamp())
        forfeited += lot.remaining
    return forfeited


def expire_member(conn, member, lots, policy, posted_on):
    """Book the expiry (or forfeiture) of one member's due lots.

    Returns ``{"member_id", "expired": {source: points}, "forfeited", "lots"}``.
    """
    result = {"member_id": member.id, "expired": {}, "forfeited": 0, "lots": 0}
    if policy.forfeits(member):
        result["forfeited"] = forfeit_member(conn, member, lots, posted_on)
        result["lots"] = len(lots)
        return result
    if policy.exempt(member):
        return result
    expired = Counter()
    for lot in policy.due_lots(lots):
        store.close_lot(conn, lot.id, posted_on)
        store.insert_ledger(conn, member.id, posted_on, LEDGER_EXPIRE, -lot.remaining, lot.id, audit.stamp())
        expired[lot.source] += lot.remaining
        result["lots"] += 1
    result["expired"] = dict(expired)
    return result


class ExpiryTotals:
    """Totals of the expiry stage, for the log and the reports."""

    def __init__(self):
        self.expired = Counter()
        self.forfeited = 0
        self.members_expired = 0
        self.members_forfeited = 0
        self.members_exempt = 0
        self.lots = 0

    def add(self, result, exempt):
        if exempt:
            self.members_exempt += 1
        if result["expired"]:
            self.members_expired += 1
            self.expired.update(result["expired"])
        if result["forfeited"]:
            self.members_forfeited += 1
            self.forfeited += result["forfeited"]
        self.lots += result["lots"]

    @property
    def expired_points(self):
        return sum(self.expired.values())

    def as_dict(self):
        return {
            "expired_points": self.expired_points,
            "expired_by_source": dict(sorted(self.expired.items())),
            "members_with_expiry": self.members_expired,
            "forfeited_points": self.forfeited,
            "closed_accounts_forfeited": self.members_forfeited,
            "members_exempt": self.members_exempt,
            "lots_closed": self.lots,
        }


def expire_batch(conn, batch, policy, posted_on, totals):
    """Expire one batch of members in one transaction; returns their results."""
    lots = store.open_lots_of(conn, [member.id for member in batch])
    results = []
    with store.transaction(conn):
        for member in batch:
            result = expire_member(conn, member, lots[member.id], policy, posted_on)
            totals.add(result, policy.exempt(member) and not policy.forfeits(member))
            results.append(result)
    return results
