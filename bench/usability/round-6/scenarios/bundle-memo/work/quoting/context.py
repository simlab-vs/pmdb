"""The pricing context of a quote: who buys, where, through which channel."""

from typing import NamedTuple

from .catalog import TIERS

CHANNELS = ("web", "store", "phone")


class PricingContext(NamedTuple):
    customer: str
    region: str
    currency: str
    tier: str
    channel: str
    date: str

    def cache_key(self):
        """Key under which results priced for this context can be reused."""
        return (self.currency, self.tier, self.channel, self.date)


class ContextError(ValueError):
    """An order can't be priced as given."""


def make_context(customer, order, region, date):
    """Build the PricingContext of ``order`` placed by ``customer``."""
    tier = customer["tier"] or "retail"
    if tier not in TIERS:
        raise ContextError(f"customer {customer['id']} has unknown tier {tier!r}")
    channel = order.get("channel", "web")
    if channel not in CHANNELS:
        raise ContextError(f"order {order['id']} has unknown channel {channel!r}")
    if channel == "phone" and tier == "retail":
        channel = "store"
    return PricingContext(
        customer=customer["id"],
        region=region.code,
        currency=region.currency,
        tier=tier,
        channel=channel,
        date=date,
    )
