"""Turning an order into a quote."""

from .cart import CartError, build_cart, units
from .catalog import CatalogError
from .context import ContextError, make_context
from . import engine
from .regions import RegionError, region_of
from .shipping import shipping_charge
from .tax import reverse_charge, vat_amount

REJECTIONS = (CartError, CatalogError, ContextError, RegionError)


def quote_order(order, customer, regions, date):
    """Price ``order`` placed by ``customer`` and return its quote as a dict.

    An order that can't be priced gets a quote with status ``rejected`` and
    the reason; ``customer`` is None for an unknown customer.
    """
    base = {"id": order["id"], "customer": order["customer"]}
    if customer is None:
        return dict(base, status="rejected", reason="unknown customer")
    try:
        region = region_of(regions, customer["country"])
        ctx = make_context(customer, order, region, date)
        cart = build_cart(order["lines"])
        if not cart:
            return dict(base, status="rejected", reason="empty cart")
        engine.prepare(ctx)
        best = engine.best_price(cart, ctx)
        listed = engine.list_price(cart, ctx)
    except REJECTIONS as exc:
        return dict(base, status="rejected", reason=str(exc))
    subtotal = best["total"]
    shipping = shipping_charge(subtotal, units(cart), ctx, region)
    vat = vat_amount(subtotal + shipping, customer, region)
    return dict(
        base,
        status="ok",
        region=region.code,
        currency=region.currency,
        tier=ctx.tier,
        channel=ctx.channel,
        units=units(cart),
        list_price=listed,
        savings=listed - subtotal,
        subtotal=subtotal,
        shipping=shipping,
        vat=vat,
        reverse_charge=reverse_charge(customer, region),
        total=subtotal + shipping + vat,
        lines=engine.merge_lines(best["lines"]),
    )
