"""The end-of-day files.

- ``eod-balances-<date>.csv`` for the issuing bank: per card, the day's net
  movement and the amount held at the end of the run.
- ``settlement-<date>.json`` and ``.txt``: totals per posting kind and per
  merchant group, which finance reconciles against the bank's settlement
  report.
"""

import json
import logging
from pathlib import Path

from . import holds, postings
from .money import fmt, plain

log = logging.getLogger(__name__)


def write_balances(out_dir, business_date, currency):
    path = Path(out_dir) / f"eod-balances-{business_date}.csv"
    movement = postings.movement()
    held = holds.outstanding()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("card,currency,movement,held\n")
        for card in sorted(set(movement) | set(held) | set(postings.cards())):
            handle.write(f"{card},{currency},{plain(movement.get(card, 0))},{plain(held.get(card, 0))}\n")
    return path


def summary(business_date, settings, stats):
    totals = postings.totals()
    movement = postings.movement()
    held = holds.outstanding()
    return {
        "business_date": business_date,
        "programme": settings.programme_id,
        "currency": settings.currency,
        "totals": {
            **totals,
            "net_movement": sum(movement.values()),
            "held": sum(held.values()),
        },
        "counts": {**postings.counts(), "open_holds": holds.open_count()},
        "clearings_by_group": postings.groups(),
        "cards": {card: {"movement": movement.get(card, 0), "held": held.get(card, 0)}
                  for card in sorted(set(movement) | set(held))},
        "run": stats,
    }


def write_summary(out_dir, business_date, settings, stats):
    data = summary(business_date, settings, stats)
    json_path = Path(out_dir) / f"settlement-{business_date}.json"
    json_path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    txt_path = Path(out_dir) / f"settlement-{business_date}.txt"
    currency = settings.currency
    totals = data["totals"]
    counts = data["counts"]
    lines = [
        f"Settlement summary {business_date}  {settings.programme} ({settings.programme_id})",
        f"Currency: {currency}",
        "",
        f"{'posting':<14}{'count':>8}{'amount':>16}",
    ]
    for kind in postings.KINDS:
        lines.append(f"{kind:<14}{counts[kind]:>8}{fmt(totals[kind]):>16}")
    lines += [
        "-" * 38,
        f"{'net movement':<22}{fmt(totals['net_movement']):>16}",
        f"{'held at close':<14}{counts['open_holds']:>8}{fmt(totals['held']):>16}",
        "",
        "Clearings by merchant group",
        f"{'group':<14}{'count':>8}{'amount':>16}",
    ]
    for group, values in data["clearings_by_group"].items():
        lines.append(f"{group:<14}{values['count']:>8}{fmt(values['amount']):>16}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, txt_path
