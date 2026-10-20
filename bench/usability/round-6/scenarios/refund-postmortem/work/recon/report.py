"""Writing the reconciliation report (text for people, JSON for the ledger import)."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .money import fmt

log = logging.getLogger(__name__)

COLUMNS = ("gross", "fees", "refunds", "disputes", "net")


def report_rows(ledger):
    rows = []
    total = dict.fromkeys(COLUMNS, 0)
    for provider, book in ledger.books.items():
        values = book.totals()
        rows.append((provider, values))
        for column in COLUMNS:
            total[column] += values[column]
    rows.append(("total", total))
    return rows


def render_text(month, currency, rows, generated_at):
    width = 16
    lines = [
        f"Payout reconciliation {month}",
        f"Settlement currency: {currency}",
        f"Generated: {generated_at}",
        "",
        f"{'provider':<10}" + "".join(f"{column:>{width}}" for column in COLUMNS),
    ]
    for provider, values in rows:
        if provider == "total":
            lines.append("-" * (10 + width * len(COLUMNS)))
        lines.append(
            f"{provider:<10}" + "".join(f"{fmt(values[c], currency):>{width}}" for c in COLUMNS)
        )
    return "\n".join(lines) + "\n"


def write_report(out_dir, month, currency, ledger):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = report_rows(ledger)
    text_path = out_dir / f"payout-recon-{month}.txt"
    text_path.write_text(render_text(month, currency, rows, generated_at))
    json_path = out_dir / f"payout-recon-{month}.json"
    payload = {
        "month": month,
        "currency": currency,
        "generated_at": generated_at,
        "providers": {provider: values for provider, values in rows if provider != "total"},
        "total": dict(rows[-1][1]),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    log.info("wrote %s and %s", text_path, json_path)
    return rows
