"""Consumption from register readings.

A meter's consumption over the period is the advance of its register between
its first and last reading, times its current-transformer ratio.  Registers
with dials roll over to zero after ``10 ** dials - 0.1`` kWh.  When a meter
is exchanged during the period, the account's consumption is the sum of the
advances of the old and the new meter.
"""

import csv
import logging
from collections import defaultdict
from typing import NamedTuple

from .accounts import UnknownAccount

log = logging.getLogger(__name__)

_MAX_PLAUSIBLE_ADVANCE = 0.9


class Exchange(NamedTuple):
    account: str
    old_meter: str
    new_meter: str
    date: str


class ImplausibleReading(ValueError):
    """A register went backwards without having rolled over."""


def load_exchanges(path, register):
    """Meter exchanges by account, from ``meter_events.csv``."""
    exchanges = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["event"].strip() != "exchange":
                continue
            try:
                account = register.resolve(row["account"])
            except UnknownAccount:
                log.warning("meter event for unknown account %s", row["account"])
                continue
            exchanges[account].append(
                Exchange(account, row["old_meter"].strip(), row["new_meter"].strip(), row["date"].strip())
            )
    return dict(exchanges)


def register_advance(first, last):
    """Advance of a register from reading ``first`` to reading ``last``."""
    advance = last.value - first.value
    if advance >= 0:
        return advance
    if last.dials:
        capacity = 10 ** last.dials
        if first.value > _MAX_PLAUSIBLE_ADVANCE * capacity:
            return advance + capacity
    raise ImplausibleReading(
        f"meter {last.meter}: register went from {first.value} to {last.value}"
    )


def meter_consumption(readings):
    """kWh measured by one meter, from its readings in time order."""
    first, last = readings[0], readings[-1]
    if first.multiplier != last.multiplier:
        log.warning("meter %s: CT ratio changed during the period", last.meter)
    return register_advance(first, last) * last.multiplier


def _check_exchanges(account, meters, exchanges):
    known = {exchange.old_meter for exchange in exchanges} | {exchange.new_meter for exchange in exchanges}
    for meter in meters:
        if meter not in known:
            log.warning("account %s: meter %s read without an exchange on record", account, meter)


def account_consumption(account, readings, exchanges):
    """kWh consumed on ``account`` from its readings, or None without two
    readings of the same meter."""
    by_meter = defaultdict(list)
    for reading in readings:
        by_meter[reading.meter].append(reading)
    if len(by_meter) > 1:
        _check_exchanges(account, by_meter, exchanges)
    total = 0.0
    measured = False
    for meter, meter_readings in by_meter.items():
        if len(meter_readings) < 2:
            log.debug("account %s: single reading of meter %s", account, meter)
            continue
        try:
            total += meter_consumption(meter_readings)
        except ImplausibleReading as exc:
            log.warning("account %s: %s; meter ignored", account, exc)
            continue
        measured = True
    if not measured:
        return None
    return round(total, 3)
