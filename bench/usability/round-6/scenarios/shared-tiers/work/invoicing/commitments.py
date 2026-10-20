"""Enterprise contracts: committed volumes with a negotiated discount."""

from .money import format_amount, round_cents
from .pricing import billable_quantity, price_metric


def contract_terms(spec, contract):
    """The pricing spec of a metric, extended with the terms of a contract."""
    return {
        **spec,
        "contract_id": contract["id"],
        "committed_units": contract["committed_units"],
        "discount": contract["discount_pct"] / 100,
    }


def committed_lines(terms, quantity):
    """Lines for a metric under contract: usage at the discounted price, plus a
    shortfall line when usage stays below the committed volume."""
    discount = 1 - terms["discount"]
    lines = []
    if billable_quantity(quantity, terms) > 0:
        lines.append({
            "code": terms["metric"],
            "description": f"{terms['label'][:1].upper()}{terms['label'][1:]} ({quantity:,} {terms['unit']}, "
                           f"contract {terms['contract_id']})",
            "quantity": quantity,
            "amount": round_cents(price_metric(quantity, terms) * discount),
        })
    committed = terms["committed_units"]
    if quantity < committed:
        due = (price_metric(committed, terms) - price_metric(quantity, terms)) * discount
        lines.append({
            "code": f"{terms['metric']}_shortfall",
            "description": f"Committed volume not used ({committed - quantity:,} {terms['unit']})",
            "quantity": committed - quantity,
            "amount": round_cents(due),
        })
    return lines


def commitment_note(terms, quantity, currency):
    """A note on how much of the committed volume was used."""
    committed = terms["committed_units"]
    share = quantity / committed if committed else 1.0
    value = round_cents(price_metric(committed, terms) * (1 - terms["discount"]))
    return (f"Contract {terms['contract_id']}: {share:.0%} of the committed "
            f"{committed:,} {terms['unit']} used (commitment value "
            f"{format_amount(value, currency)}).")
