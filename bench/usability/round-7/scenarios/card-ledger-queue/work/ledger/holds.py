"""Authorization holds.

An approved authorization reserves its billing amount on the card until the
merchant presents it (clearing), the authorization is reversed, or the hold
expires (holds older than the business date are expired by the nightly
balance job at the bank, not here). A clearing consumes the hold up to its
amount; a final clearing releases whatever is left. A merchant may present
more than it authorized (tips, hotel extras): the clearing is posted in full
and the hold is simply used up.
"""

from collections import Counter
from typing import NamedTuple

OPEN = "open"
CLEARED = "cleared"
REVERSED = "reversed"


class Hold(NamedTuple):
    card: str
    auth_code: str
    amount: int
    remaining: int
    state: str
    opened_at: int


_holds = {}
stats = Counter()


def reset():
    _holds.clear()
    stats.clear()


def hold_key(card, auth_code):
    return (card, auth_code)


def find(card, auth_code):
    return _holds.get(hold_key(card, auth_code))


def open_hold(card, auth_code, amount, opened_at):
    key = hold_key(card, auth_code)
    if key in _holds:
        stats["reopened"] += 1
        return _holds[key]
    hold = Hold(card, auth_code, amount, amount, OPEN, opened_at)
    _holds[key] = hold
    stats["opened"] += 1
    return hold


def consume(card, auth_code, amount, final):
    """Use ``amount`` of a hold for a clearing; returns the hold afterwards."""
    key = hold_key(card, auth_code)
    hold = _holds[key]
    remaining = max(0, hold.remaining - min(amount, hold.remaining))
    state = hold.state
    if final or remaining == 0:
        remaining = 0
        state = CLEARED
    hold = hold._replace(remaining=remaining, state=state)
    _holds[key] = hold
    stats["consumed"] += 1
    return hold


def release(card, auth_code):
    """Release what is left of a hold (authorization reversed)."""
    key = hold_key(card, auth_code)
    hold = _holds[key]
    if hold.state != OPEN:
        stats["release_ignored"] += 1
        return hold
    hold = hold._replace(remaining=0, state=REVERSED)
    _holds[key] = hold
    stats["released"] += 1
    return hold


def outstanding():
    """Per card: the amount still held at the end of the run."""
    held = Counter()
    for hold in _holds.values():
        if hold.state == OPEN and hold.remaining:
            held[hold.card] += hold.remaining
    return held


def open_count():
    return sum(1 for hold in _holds.values() if hold.state == OPEN and hold.remaining)
