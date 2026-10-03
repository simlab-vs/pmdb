"""Assembling one customer's invoice."""

import itertools
from datetime import date, timedelta

from .advisor import upgrade_suggestion
from .commitments import commitment_note, committed_lines, contract_terms
from .fx import convert
from .money import percent_of, round_cents, sum_amounts
from .pricing import base_fee_lines, usage_line
from .tax import tax_treatment


class RunContext:
    """Everything an invoice is computed from, loaded once per run."""

    def __init__(self, settings, period, plans, usage, contracts, changes, rates):
        self.numbers = itertools.count(1)
        self.settings = settings
        self.period = period
        self.plans = plans
        self.usage = usage
        self.contracts = contracts
        self.changes = changes
        self.rates = rates
        self.issue_date = date.fromisoformat(period.end) + timedelta(days=1)


def invoice_number(settings, period, sequence):
    return f"{settings.invoice_prefix}-{period.label}-{sequence:04d}"


def metered_lines(customer, plan, usage, contracts):
    """Usage lines of every metric of the plan, and the notes they produce."""
    by_metric = {contract["metric"]: contract for contract in contracts}
    lines, notes = [], []
    for metric, spec in plan["metrics"].items():
        quantity = usage.get(metric, 0)
        contract = by_metric.get(metric)
        if contract is None:
            line = usage_line(spec, quantity)
            if line is not None:
                lines.append(line)
            continue
        terms = contract_terms(spec, contract)
        lines.extend(committed_lines(terms, quantity))
        notes.append(commitment_note(terms, quantity, "EUR"))
    return lines, notes


def discount_line(customer, subtotal):
    """A negotiated percentage discount on the whole invoice, if any."""
    if not customer["discount_pct"]:
        return None
    return {
        "code": "discount",
        "description": f"Discount {customer['discount_pct']:g}%",
        "quantity": 1,
        "amount": -percent_of(subtotal, customer["discount_pct"] / 100),
    }


def in_currency(lines, currency, rates):
    """Copies of the lines with their amounts converted from EUR."""
    return [{**line, "amount": convert(line["amount"], currency, rates)} for line in lines]


def build_invoice(customer, ctx):
    """Compute the invoice of one customer for the run's period, numbering it."""
    sequence = next(ctx.numbers)
    plan = ctx.plans[customer["plan"]]
    usage = ctx.usage.get(customer["id"], {})
    lines = base_fee_lines(customer, ctx)
    usage_lines, notes = metered_lines(customer, plan, usage, ctx.contracts.get(customer["id"], []))
    lines.extend(usage_lines)
    subtotal_eur = sum_amounts(line["amount"] for line in lines)
    discount = discount_line(customer, subtotal_eur)
    if discount is not None:
        lines.append(discount)
        subtotal_eur = sum_amounts(line["amount"] for line in lines)
    if subtotal_eur < ctx.settings.minimum_invoice:
        lines.append({
            "code": "minimum",
            "description": "Minimum monthly charge",
            "quantity": 1,
            "amount": round_cents(ctx.settings.minimum_invoice - subtotal_eur),
        })
        subtotal_eur = ctx.settings.minimum_invoice
    suggestion = upgrade_suggestion(customer, plan, usage, ctx)
    if suggestion:
        notes.append(suggestion)

    currency = customer["currency"]
    lines = in_currency(lines, currency, ctx.rates)
    subtotal = sum_amounts(line["amount"] for line in lines)
    rate, tax_label = tax_treatment(customer, ctx.settings)
    tax = percent_of(subtotal, rate)
    return {
        "number": invoice_number(ctx.settings, ctx.period, sequence),
        "customer": customer["id"],
        "name": customer["name"],
        "plan": plan["id"],
        "period": ctx.period.label,
        "issued": ctx.issue_date.isoformat(),
        "due": (ctx.issue_date + timedelta(days=ctx.settings.payment_terms_days)).isoformat(),
        "currency": currency,
        "lines": lines,
        "subtotal": subtotal,
        "tax_label": tax_label,
        "tax_rate": rate,
        "tax": tax,
        "total": round_cents(subtotal + tax),
        "notes": notes,
    }
