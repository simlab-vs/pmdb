"""Stock that is still free during the run.

The run starts from the levels the inventory service reported and
reserves units as it allocates lines. Everything is kept per
``(sku, warehouse)`` in module state: the run allocates one night's lines
in one process.
"""

import logging

log = logging.getLogger(__name__)

_free = {}
_safety = {}
_bins = {}
_start = {}


class OverAllocation(RuntimeError):
    pass


def open_ledger(levels):
    _free.clear()
    _safety.clear()
    _bins.clear()
    _start.clear()
    for key, level in levels.items():
        _free[key] = level.available
        _start[key] = level.available
        _safety[key] = level.safety_stock
        _bins[key] = level.bin
    return len(_free)


def stocks(sku, warehouse):
    return (sku, warehouse) in _free


def remaining(sku, warehouse):
    return _free.get((sku, warehouse), 0)


def safety_stock(sku, warehouse):
    return _safety.get((sku, warehouse), 0)


def bin_of(sku, warehouse):
    return _bins.get((sku, warehouse), "")


def reserve(sku, warehouse, qty):
    """Take ``qty`` units of the remaining stock."""
    key = (sku, warehouse)
    if qty > _free.get(key, 0):
        raise OverAllocation(f"{qty} x {sku} in {warehouse}: only {_free.get(key, 0)} left")
    _free[key] -= qty


def negative_locations():
    return [key for key, free in _free.items() if free < 0]


def reserved_by_warehouse():
    """Units reserved by this run, per warehouse."""
    totals = {}
    for (sku, warehouse), start in _start.items():
        totals[warehouse] = totals.get(warehouse, 0) + start - _free[(sku, warehouse)]
    return totals
