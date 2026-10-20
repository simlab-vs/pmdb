"""Pricing of metered usage and subscription fees."""

from .config import days_between
from .money import round_cents


class PricingError(ValueError):
    pass


def graduated_charge(quantity, tiers):
    """Each unit is charged at the price of the tier it falls in."""
    total = 0.0
    for tier in tiers:
        if quantity <= tier.start:
            continue
        top = quantity if tier.upto is None else min(quantity, tier.upto)
        total += (top - tier.start) * tier.unit_price
    return total


def volume_charge(quantity, tiers):
    """All units are charged at the price of the tier the total quantity falls in."""
    for tier in tiers:
        if tier.upto is None or quantity <= tier.upto:
            return quantity * tier.unit_price
    raise PricingError(f"no tier covers a quantity of {quantity}")


def billable_quantity(quantity, spec):
    """Usage beyond the units included in the plan's base fee."""
    return max(0, quantity - spec["included"])


def price_metric(quantity, spec):
    """Charge for ``quantity`` units of a metric under its pricing spec, unrounded."""
    billable = billable_quantity(quantity, spec)
    if billable == 0:
        return 0.0
    if spec["model"] == "volume":
        return volume_charge(billable, spec["tiers"])
    return graduated_charge(billable, spec["tiers"])


def usage_line(spec, quantity):
    """The invoice line for a metric, or ``None`` when nothing is billable."""
    billable = billable_quantity(quantity, spec)
    if billable == 0:
        return None
    return {
        "code": spec["metric"],
        "description": f"{spec['label'][:1].upper()}{spec['label'][1:]} ({quantity:,} {spec['unit']}, "
                       f"{spec['included']:,} included)",
        "quantity": quantity,
        "amount": round_cents(price_metric(quantity, spec)),
    }


def plan_segments(customer, history, period):
    """Split the period into ``(plan id, first day, last day)`` segments by the
    customer's plan changes during the period."""
    if not history:
        return [(customer["plan"], period.start, period.end)]
    segments = []
    plan, first = history[0]["from_plan"], period.start
    for change in history:
        if change["effective"] > first:
            segments.append((plan, first, _day_before(change["effective"])))
        plan, first = change["to_plan"], change["effective"]
    segments.append((plan, first, period.end))
    return segments


def _day_before(iso_day):
    from datetime import date, timedelta
    return (date.fromisoformat(iso_day) - timedelta(days=1)).isoformat()


def base_fee_lines(customer, ctx):
    """Subscription fee lines, prorated by day when the plan changed in the period."""
    period = ctx.period
    lines = []
    for plan_id, first, last in plan_segments(customer, ctx.changes.get(customer["id"], []), period):
        plan = ctx.plans[plan_id]
        days = days_between(first, last)
        fee = plan["base_fee"] * days / period.days
        if days == period.days:
            description = f"{plan['name']} plan, {period.label}"
        else:
            description = f"{plan['name']} plan, {first} to {last} ({days} days)"
        lines.append({
            "code": "base_fee",
            "description": description,
            "quantity": days,
            "amount": round_cents(fee),
        })
    return lines
