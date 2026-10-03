"""The payroll register: totals per cost centre and for the company."""

from collections import Counter

from .models import HOURLY, SALARIED

COLUMNS = (
    "base_salary",
    "hourly_pay",
    "premiums",
    "allowances",
    "gross",
    "employee_contributions",
    "tax",
    "net",
    "employer_contributions",
)


class Register:
    def __init__(self, cost_centres):
        self.cost_centres = dict(cost_centres)
        self.rows = {code: Counter() for code in self.cost_centres}
        self.heads = {code: Counter() for code in self.cost_centres}

    def add(self, payslip):
        row = self.rows[payslip.cost_centre]
        for column in COLUMNS:
            row[column] += getattr(payslip, column)
        self.heads[payslip.cost_centre][payslip.pay_type] += 1

    def headcount(self, code):
        heads = self.heads[code]
        return heads[SALARIED] + heads[HOURLY]

    def totals(self):
        total = Counter()
        for row in self.rows.values():
            for column in COLUMNS:
                total[column] += row[column]
        return {column: total[column] for column in COLUMNS}

    def by_cost_centre(self):
        for code in sorted(self.cost_centres):
            row = self.rows[code]
            yield code, {column: row[column] for column in COLUMNS}, dict(self.heads[code])

    def total_heads(self):
        return sum(self.headcount(code) for code in self.cost_centres)
