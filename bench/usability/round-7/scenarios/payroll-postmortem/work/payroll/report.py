"""Writing the payroll register for finance (text) and the GL import (JSON)."""

import json
import logging
import time
from pathlib import Path

from .money import fmt
from .register import COLUMNS

log = logging.getLogger(__name__)

HEADINGS = ("base", "hourly", "premiums", "allowances", "gross", "ee contrib", "tax", "net", "er contrib")


def write_report(out_dir, period, rules, register):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"payroll-register-{period.month}"
    text_path, json_path = out / f"{stem}.txt", out / f"{stem}.json"

    lines = [
        f"Payroll register {period.month}  {rules.company}",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        f"{'cost centre':<22}{'heads':>6}" + "".join(f"{h:>14}" for h in HEADINGS),
    ]
    data = {"period": period.month, "cost_centres": {}, "totals": {}}
    for code, row, heads in register.by_cost_centre():
        name = f"{code} {rules.cost_centres[code]}"[:21]
        count = sum(heads.values())
        lines.append(f"{name:<22}{count:>6}" + "".join(f"{fmt(row[c]):>14}" for c in COLUMNS))
        data["cost_centres"][code] = dict(row, headcount=count, **{f"heads_{k}": v for k, v in sorted(heads.items())})
    totals = register.totals()
    lines.append("-" * (28 + 14 * len(COLUMNS)))
    lines.append(f"{'total':<22}{register.total_heads():>6}" + "".join(f"{fmt(totals[c]):>14}" for c in COLUMNS))
    data["totals"] = dict(totals, headcount=register.total_heads())

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log.info("wrote %s and %s", text_path, json_path)
    return totals
