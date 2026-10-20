"""The credit-transfer file for the bank (one transfer per payslip)."""

import csv
import logging
from pathlib import Path

from .money import fmt

log = logging.getLogger(__name__)


def remittance(period, person_id):
    return f"Lohn/Gehalt {period.month} {person_id}"


def write_bank_file(bank_dir, period, rules, payslips):
    """Write ``credit-transfers-YYYY-MM.csv``; returns (transfers, total cents)."""
    path = Path(bank_dir) / f"credit-transfers-{period.month}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    count = total = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["debtor_iban", "creditor_name", "creditor_iban", "amount", "remittance"])
        for person, payslip in payslips:
            if payslip.net <= 0:
                continue
            writer.writerow([rules.debtor_iban, person.name, person.iban, fmt(payslip.net).replace(",", ""),
                             remittance(period, person.id)])
            count += 1
            total += payslip.net
    log.info("wrote %d credit transfers, %s EUR, to %s", count, fmt(total), path)
    return count, total
