"""Meter reading feeds from the meter operators.

Each operator delivers its readings for the month in its own format:

* Telemetrix: ``tx_*.csv``, semicolon-separated, decimal commas, local times
  as ``DD.MM.YYYY HH:MM``, registers in kWh with a number of dials;
* GridSense: ``gs_*.csv``, comma-separated, ISO timestamps, registers in kWh
  and a current-transformer ratio for large supplies;
* Meterline: ``ml_*.jsonl``, one JSON object per line, Unix timestamps and
  registers in Wh (smart meters, which don't roll over).

All of them become :class:`Reading` records, merged into one stream ordered
by account, meter and time.
"""

import csv
import heapq
import json
import logging
from datetime import datetime, timezone
from typing import NamedTuple

from . import periods

log = logging.getLogger(__name__)


class Reading(NamedTuple):
    account: str
    meter: str
    taken_at: str
    value: float
    dials: int
    multiplier: float
    kind: str
    source: str


class FeedError(ValueError):
    """A record of a feed couldn't be parsed."""


_TELEMETRIX_KINDS = {"RT": "routine", "AU": "removal", "EI": "install", "KS": "routine"}
_GRIDSENSE_KINDS = {"scheduled": "routine", "special": "routine", "final": "removal", "initial": "install"}
_METERLINE_KINDS = {"periodic": "routine", "on_demand": "routine", "commissioning": "install", "decommissioning": "removal"}


def _decimal_comma(text):
    return float(text.strip().replace(".", "").replace(",", "."))


def parse_telemetrix(row):
    try:
        taken = datetime.strptime(row["READ_AT"].strip(), "%d.%m.%Y %H:%M")
        return Reading(
            account=row["ACCOUNT"].strip(),
            meter=row["METER"].strip(),
            taken_at=taken.isoformat(timespec="minutes"),
            value=_decimal_comma(row["REGISTER"]),
            dials=int(row["DIALS"]),
            multiplier=1.0,
            kind=_TELEMETRIX_KINDS[row["REASON"].strip()],
            source="telemetrix",
        )
    except (KeyError, ValueError) as exc:
        raise FeedError(f"telemetrix record {dict(row)}: {exc}") from exc


def parse_gridsense(row):
    try:
        ratio = row["ct_ratio"].strip()
        return Reading(
            account=row["account_ref"].strip(),
            meter=row["meter_serial"].strip(),
            taken_at=datetime.fromisoformat(row["timestamp"].strip()).isoformat(timespec="minutes"),
            value=float(row["reading_kwh"]),
            dials=6,
            multiplier=float(ratio) if ratio else 1.0,
            kind=_GRIDSENSE_KINDS[row["read_type"].strip()],
            source="gridsense",
        )
    except (KeyError, ValueError) as exc:
        raise FeedError(f"gridsense record {dict(row)}: {exc}") from exc


def parse_meterline(record):
    try:
        taken = datetime.fromtimestamp(int(record["ts"]), tz=timezone.utc).replace(tzinfo=None)
        return Reading(
            account=str(record["acct"]).strip(),
            meter=str(record["device"]).strip(),
            taken_at=taken.isoformat(timespec="minutes"),
            value=int(record["wh"]) / 1000,
            dials=0,
            multiplier=1.0,
            kind=_METERLINE_KINDS[record["event"]],
            source="meterline",
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FeedError(f"meterline record {record}: {exc}") from exc


def _read_csv(path, delimiter, parse):
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter=delimiter):
            yield parse(row)


def _read_jsonl(path, parse):
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FeedError(f"{path.name}:{number}: {exc}") from exc
            yield parse(record)


SOURCES = (
    ("telemetrix", "tx_*.csv", lambda path: _read_csv(path, ";", parse_telemetrix)),
    ("gridsense", "gs_*.csv", lambda path: _read_csv(path, ",", parse_gridsense)),
    ("meterline", "ml_*.jsonl", lambda path: _read_jsonl(path, parse_meterline)),
)


def reading_order(reading):
    """Readings are processed account by account, each meter's in time order."""
    return (reading.account, reading.meter, reading.taken_at)


def _deduplicate(readings):
    """Drop repeated deliveries of the same reading (same meter and time)."""
    seen = set()
    unique = []
    for reading in readings:
        key = (reading.meter, reading.taken_at)
        if key in seen:
            continue
        seen.add(key)
        unique.append(reading)
    return unique


def load_source(name, paths, reader, period):
    """All readings of one operator within ``period``, sorted for merging."""
    readings = []
    outside = 0
    for path in paths:
        for reading in reader(path):
            if periods.in_window(period, reading.taken_at):
                readings.append(reading)
            else:
                outside += 1
    unique = _deduplicate(readings)
    unique.sort(key=reading_order)
    log.info(
        "%s: %d readings from %d file(s) (%d duplicates, %d outside %s)",
        name, len(unique), len(paths), len(readings) - len(unique), outside, period.label,
    )
    return unique


def load_all(feed_dir, period):
    """Readings of every operator, merged in :func:`reading_order`."""
    streams = []
    for name, pattern, reader in SOURCES:
        paths = sorted(feed_dir.glob(pattern))
        if not paths:
            log.warning("%s: no files matching %s in %s", name, pattern, feed_dir)
            continue
        streams.append(load_source(name, paths, reader, period))
    merged = list(heapq.merge(*streams, key=reading_order))
    log.info("feeds: %d readings in total", len(merged))
    return merged
