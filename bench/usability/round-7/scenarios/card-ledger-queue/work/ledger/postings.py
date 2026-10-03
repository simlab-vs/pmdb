"""Card ledger postings for the business date.

Every posting moves money on one card: top-ups and refunds credit it,
clearings and fees debit it. Postings are summed per card (the balance
file) and per posting kind and merchant group (the settlement summary).
"""

from collections import Counter
from typing import NamedTuple

TOPUP = "topup"
REFUND = "refund"
CLEARING = "clearing"
FX_FEE = "fx_fee"
ATM_FEE = "atm_fee"

CREDITS = frozenset({TOPUP, REFUND})
KINDS = (CLEARING, REFUND, TOPUP, FX_FEE, ATM_FEE)


class Posting(NamedTuple):
    card: str
    kind: str
    amount: int
    group: str
    ref: str


_movement = Counter()
_totals = Counter()
_counts = Counter()
_groups = {}
_cards = set()


def reset():
    _movement.clear()
    _totals.clear()
    _counts.clear()
    _groups.clear()
    _cards.clear()


def post(posting):
    """Book one posting; returns the signed amount it moved on the card."""
    signed = posting.amount if posting.kind in CREDITS else -posting.amount
    _movement[posting.card] += signed
    _totals[posting.kind] += posting.amount
    _counts[posting.kind] += 1
    _cards.add(posting.card)
    if posting.kind == CLEARING:
        group = _groups.setdefault(posting.group, Counter())
        group["count"] += 1
        group["amount"] += posting.amount
    return signed


def touch(card):
    """Note a card that had activity (e.g. a hold) without a posting."""
    _cards.add(card)


def movement():
    return dict(_movement)


def totals():
    return {kind: _totals[kind] for kind in KINDS}


def counts():
    return {kind: _counts[kind] for kind in KINDS}


def groups():
    return {group: dict(values) for group, values in sorted(_groups.items())}


def cards():
    return sorted(_cards)
