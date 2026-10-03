"""Consistency checks before the files go to the bank."""

import logging

from . import postings
from .money import fmt

log = logging.getLogger(__name__)


class CheckFailed(RuntimeError):
    pass


def check_balanced():
    """The per-card movements must add up to the posting totals."""
    totals = postings.totals()
    expected = (
        totals[postings.TOPUP] + totals[postings.REFUND]
        - totals[postings.CLEARING] - totals[postings.FX_FEE] - totals[postings.ATM_FEE]
    )
    actual = sum(postings.movement().values())
    if actual != expected:
        raise CheckFailed(f"card movements sum to {fmt(actual)}, postings to {fmt(expected)}")


def check_overdrawn(limit=0):
    """Report cards whose day's movement is a large debit (informational)."""
    heavy = [card for card, amount in postings.movement().items() if amount < -50000]
    if heavy:
        log.info("%d cards moved more than 500.00 out today", len(heavy))
    return heavy


def check_stats(dedup_stats, received):
    handled = sum(dedup_stats[k] for k in ("new", "redelivery", "resend"))
    if handled != received:
        raise CheckFailed(f"received {received} messages but classified {handled}")
