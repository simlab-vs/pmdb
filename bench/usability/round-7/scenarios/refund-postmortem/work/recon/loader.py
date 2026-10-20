"""Reading the provider event export.

The export is JSON Lines, optionally gzip-compressed, one provider event per
line, as delivered by the payments gateway's webhook archiver. Webhooks are
delivered at least once, so the same event can appear more than once; the
archiver also includes a few hours of the neighbouring months.
"""

import gzip
import json
import logging
from collections import Counter

from .models import RawEvent
from .timeutil import parse_epoch, iso

log = logging.getLogger(__name__)


class ExportError(ValueError):
    pass


def open_export(path):
    path = str(path)
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8")


TIMESTAMP_FIELDS = {"lumen": "eventDate"}


def read_raw_events(path, providers, stats):
    """Yield a RawEvent per line for the configured providers."""
    skipped = Counter()
    with open_export(path) as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                body = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExportError(f"{path}:{number}: {exc}") from exc
            provider = body.get("provider")
            if provider not in providers:
                skipped[provider] += 1
                continue
            created = body[TIMESTAMP_FIELDS.get(provider, "created")]
            stats["read"] += 1
            yield RawEvent(provider, body["id"], parse_epoch(created), body)
    for provider, count in sorted(skipped.items(), key=lambda kv: str(kv[0])):
        log.info("ignored %d events of provider %s", count, provider)


def deduplicate(events, stats):
    """Drop repeated deliveries of the same event, keeping the first one."""
    seen = set()
    for event in events:
        key = (event.provider, event.event_id)
        if key in seen:
            stats["redelivered"] += 1
            continue
        seen.add(key)
        yield event


def in_window(events, start, end, stats):
    """Keep the events created in ``[start, end)``."""
    for event in events:
        if start <= event.ts < end:
            yield event
        else:
            stats["outside"] += 1


def load_export(path, providers, start, end):
    """Read, de-duplicate and window the export; yield its events in time order."""
    stats = Counter()
    events = in_window(deduplicate(read_raw_events(path, providers, stats), stats), start, end, stats)
    ordered = sorted(events, key=lambda event: (event.ts, event.provider, event.event_id))
    log.info("read %d events from %s", stats["read"], path)
    if stats["redelivered"]:
        log.info("dropped %d redelivered events", stats["redelivered"])
    log.info("dropped %d events outside %s .. %s", stats["outside"], iso(start), iso(end))
    yield from ordered
