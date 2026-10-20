"""Metered usage: daily records exported by the metering service."""

import csv
from collections import defaultdict


class UsageError(ValueError):
    pass


def load_usage(path, period, aggregations):
    """Aggregate the period's daily usage records per customer and metric.

    Returns ``{customer id: {metric: quantity}}``. Records are deduplicated by
    their ``record_id`` (the exporter retries failed uploads). ``sum`` metrics
    add daily quantities, including negative corrections; ``average`` metrics
    (storage) average the daily snapshots over the days of the period; ``max``
    metrics (seats) take the peak.
    """
    seen = set()
    daily = defaultdict(lambda: defaultdict(float))
    peaks = defaultdict(dict)
    skipped = 0
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            if row["record_id"] in seen:
                continue
            seen.add(row["record_id"])
            day = row["date"]
            if not period.start <= day <= period.end:
                skipped += 1
                continue
            metric = row["metric"]
            aggregate = aggregations.get(metric)
            if aggregate is None:
                skipped += 1
                continue
            try:
                quantity = float(row["quantity"])
            except ValueError:
                raise UsageError(f"record {row['record_id']}: bad quantity {row['quantity']!r}") from None
            customer = row["customer"]
            if aggregate == "max":
                peaks[customer][metric] = max(peaks[customer].get(metric, 0.0), quantity)
            else:
                daily[customer][metric] += quantity
    usage = {}
    for customer in set(daily) | set(peaks):
        totals = {}
        for metric, quantity in daily[customer].items():
            if aggregations[metric] == "average":
                quantity = quantity / period.days
            totals[metric] = max(0, round(quantity))
        for metric, quantity in peaks[customer].items():
            totals[metric] = round(quantity)
        usage[customer] = totals
    return usage, skipped


def usage_of(usage, customer_id, metric):
    """Quantity of ``metric`` used by a customer, 0 if none was recorded."""
    return usage.get(customer_id, {}).get(metric, 0)
