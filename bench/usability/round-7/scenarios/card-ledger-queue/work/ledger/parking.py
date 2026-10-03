"""Events that arrived ahead of their authorization.

The queue doesn't keep order, and acquirers sometimes present a transaction
within seconds of its authorization, so a clearing or a reversal can arrive
before the authorization it refers to. Such events are parked under the
authorization they reference and handled as soon as the authorization
arrives. Whatever is still parked when the queue is drained refers to an
authorization from an earlier business date (a late presentment) and is
posted without a hold.
"""

from collections import Counter

_parked = {}
stats = Counter()


def reset():
    _parked.clear()
    stats.clear()


def park(message):
    data = message.data
    key = (data["card"], data["auth_code"])
    _parked.setdefault(key, []).append(message)
    stats["parked"] += 1
    stats[f"parked.{message.event_type}"] += 1


def take(card, auth_code):
    """The events parked under an authorization, in the order they arrived."""
    waiting = _parked.pop((card, auth_code), [])
    stats["released"] += len(waiting)
    return waiting


def leftovers():
    """Everything still parked, oldest authorization reference first."""
    remaining = []
    for key in sorted(_parked):
        remaining.extend(_parked[key])
    _parked.clear()
    stats["unmatched"] += len(remaining)
    return remaining


def count():
    return sum(len(waiting) for waiting in _parked.values())
