"""The allocation summary for operations (text) and the OMS import (JSON)."""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

from .models import CHANNELS
from .timeutil import iso, utc_now

log = logging.getLogger(__name__)


def summarize(allocations, warehouses):
    by_warehouse = {code: {"lines": 0, "units": 0, "orders": 0} for code in warehouses}
    orders = defaultdict(set)
    by_channel = {c: Counter() for c in CHANNELS}
    backorders = []
    reasons = Counter()
    for allocation in allocations:
        channel = by_channel[allocation.channel]
        channel["lines"] += 1
        channel["ordered"] += allocation.ordered
        channel["backordered"] += allocation.backordered
        channel["allocated"] += allocation.ordered - allocation.backordered
        for pick in allocation.picks:
            stats = by_warehouse[pick.warehouse]
            stats["lines"] += 1
            stats["units"] += pick.qty
            orders[pick.warehouse].add(allocation.order_id)
        if allocation.backordered:
            reasons[allocation.reason] += 1
            backorders.append(
                {
                    "order_id": allocation.order_id,
                    "line_no": allocation.line_no,
                    "sku": allocation.sku,
                    "qty": allocation.backordered,
                    "reason": allocation.reason,
                }
            )
    for code, stats in by_warehouse.items():
        stats["orders"] = len(orders[code])
    return {
        "warehouses": by_warehouse,
        "channels": {c: dict(v) for c, v in by_channel.items()},
        "backorder_reasons": dict(reasons),
        "backorders": backorders,
    }


def write_summary(report_dir, day, summary, names):
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    generated = iso(utc_now())
    json_path = report_dir / f"allocation-{day}.json"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump({"day": day, "generated_at": generated, **summary}, handle, indent=1, sort_keys=True)
    text_path = report_dir / f"allocation-{day}.txt"
    lines = [f"Order allocation {day}", f"Generated: {generated}", ""]
    lines.append(f"{'warehouse':<14}{'orders':>8}{'lines':>8}{'units':>9}")
    for code, stats in summary["warehouses"].items():
        lines.append(f"{names[code]:<14}{stats['orders']:>8}{stats['lines']:>8}{stats['units']:>9}")
    lines.append("")
    lines.append(f"{'channel':<14}{'lines':>8}{'ordered':>9}{'allocated':>11}{'backordered':>13}")
    for channel, stats in summary["channels"].items():
        lines.append(
            f"{channel:<14}{stats.get('lines', 0):>8}{stats.get('ordered', 0):>9}"
            f"{stats.get('allocated', 0):>11}{stats.get('backordered', 0):>13}"
        )
    lines.append("")
    lines.append(f"Backordered lines: {len(summary['backorders'])}")
    for reason, count in sorted(summary["backorder_reasons"].items()):
        lines.append(f"  {reason}: {count}")
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("wrote %s and %s", text_path, json_path)
    return text_path, json_path
