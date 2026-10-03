"""Plan recommendations printed on invoices of customers who outgrow their plan."""

from operator import attrgetter

from .money import format_rate
from .pricing import billable_quantity
from .util import first, ranked

UPGRADE_PATHS = {"starter": "growth", "growth": "scale"}
ADVISED_METRIC = "api_requests"


def top_tier(tiers):
    """The open-ended tier, where a plan's volume discount ends."""
    return max(tiers, key=attrgetter("start"))


def best_rate_reached(tiers, units):
    """The lowest unit price among the tiers that ``units`` reach."""
    by_price = ranked(tiers, key=attrgetter("unit_price"))
    return first(by_price, lambda tier: units > tier.start, default=by_price[-1])


def upgrade_suggestion(customer, plan, usage, ctx):
    """A note for self-serve customers whose API volume reached the top tier of
    their plan, quoting the rate the next plan up would give them."""
    target_id = UPGRADE_PATHS.get(plan["id"])
    if target_id is None or customer["segment"] == "enterprise":
        return None
    target = ctx.plans[target_id]
    current_spec = plan["metrics"].get(ADVISED_METRIC)
    target_spec = target["metrics"].get(ADVISED_METRIC)
    if target.get("retired") or current_spec is None or target_spec is None:
        return None
    used = usage.get(ADVISED_METRIC, 0)
    current = top_tier(current_spec["tiers"])
    if billable_quantity(used, current_spec) <= current.start:
        return None
    offered = best_rate_reached(target_spec["tiers"], billable_quantity(used, target_spec))
    if offered.unit_price >= current.unit_price:
        return None
    return (f"Your {current_spec['label']} volume ({used:,} {current_spec['unit']}) reached "
            f"the top tier of the {plan['name']} plan, billed at "
            f"{format_rate(current.unit_price)} EUR. On the {target['name']} plan it would be "
            f"billed at {format_rate(offered.unit_price)} EUR per {target_spec['unit'][:-1]}.")
