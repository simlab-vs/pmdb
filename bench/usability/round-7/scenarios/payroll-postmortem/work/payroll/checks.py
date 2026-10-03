"""Checks run before the bank file is released."""

import logging

from .money import fmt

log = logging.getLogger(__name__)


class CheckFailed(RuntimeError):
    pass


def check_payslip(payslip):
    problems = []
    if payslip.net < 0:
        problems.append(f"negative net {fmt(payslip.net)}")
    if payslip.tax < 0 or payslip.employee_contributions < 0:
        problems.append("negative deductions")
    if payslip.base_salary and payslip.hourly_pay and payslip.days > 20:
        problems.append("salary and hourly pay in one month")
    return problems


def check_run(payslips, register):
    """Fail the run on inconsistent payslips; log the totals for the four-eyes check."""
    flagged = 0
    for _, payslip in payslips:
        problems = check_payslip(payslip)
        if problems:
            flagged += 1
            log.warning("%s: %s", payslip.person, "; ".join(problems))
    totals = register.totals()
    if sum(p.net for _, p in payslips) != totals["net"]:
        raise CheckFailed("register net differs from the payslips' net")
    if flagged > len(payslips) // 100:
        raise CheckFailed(f"{flagged} payslips flagged")
    log.info(
        "checks passed: %d payslips, gross %s, net %s, employer contributions %s",
        len(payslips),
        fmt(totals["gross"]),
        fmt(totals["net"]),
        fmt(totals["employer_contributions"]),
    )
