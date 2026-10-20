"""Audit trail of a run: who booked what, when.

Ledger entries carry the wall-clock time at which they were booked
(``created_at``), separately from the business date they belong to.
"""

import logging

from . import clock

log = logging.getLogger(__name__)

_run = {"id": None, "stamps": 0}


def begin(run_id):
    _run["id"] = run_id
    _run["stamps"] = 0


def stamp():
    """Time stamp for a booking made now."""
    _run["stamps"] += 1
    return clock.stamp()


def run_id():
    return _run["id"]


def bookings():
    return _run["stamps"]
