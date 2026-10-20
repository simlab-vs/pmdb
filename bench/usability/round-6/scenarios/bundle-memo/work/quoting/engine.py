"""Pricing carts: the cheapest way to pay for a cart with the offers of the day.

The search takes the first unit of the cart (in SKU order) and tries every
way to pay for it: at its unit price, or as part of one use of an eligible
offer.  It then prices what is left of the cart the same way, so the same
sub-carts come up again and again; their results are kept.
"""

import logging

from . import catalog
from .cart import cart_key, first_sku, remove_units
from .offers import eligible_offers, index_by_sku, offer_applications

log = logging.getLogger(__name__)

EMPTY = {"total": 0, "lines": []}

_offers = []
_offers_by_key = {}
_results = {}
stats = {"searched": 0, "reused": 0}


def configure(offers):
    """Use ``offers`` from now on, and forget every earlier result."""
    _offers[:] = offers
    _offers_by_key.clear()
    _results.clear()
    stats.update(searched=0, reused=0)


def prepare(ctx):
    """Select the offers usable in ``ctx``; return how many there are."""
    key = ctx.cache_key()
    if key not in _offers_by_key:
        usable = eligible_offers(_offers, ctx)
        _offers_by_key[key] = index_by_sku(usable)
        log.debug("%d offers for %s", len(usable), key)
    return len(_offers_by_key[key])


def _line(offer, take, amount):
    return {"offer": offer, "units": dict(take), "amount": amount}


def _with(line, rest):
    return {"total": line["amount"] + rest["total"], "lines": [line] + rest["lines"]}


def best_price(cart, ctx):
    """Return the cheapest way to pay for ``cart`` in ``ctx``.

    The result is a dict with the ``total`` in minor units and the
    ``lines`` making it up, each with the ``offer`` used (``""`` for units
    paid at their unit price), the ``units`` it covers and its ``amount``.
    :func:`prepare` must have been called for ``ctx``.
    """
    if not cart:
        return EMPTY
    key = (cart_key(cart), ctx.cache_key())
    known = _results.get(key)
    if known is not None:
        stats["reused"] += 1
        return known
    stats["searched"] += 1
    sku = first_sku(cart)
    unit = catalog.unit_price(sku, ctx)
    best = _with(_line("", {sku: 1}, unit), best_price(remove_units(cart, {sku: 1}), ctx))
    for offer in _offers_by_key[ctx.cache_key()].get(sku, ()):
        for app in offer_applications(offer, cart, sku, ctx):
            rest = best_price(remove_units(cart, app.take), ctx)
            if app.amount + rest["total"] < best["total"]:
                best = _with(_line(app.offer, app.take, app.amount), rest)
    _results[key] = best
    return best


def list_price(cart, ctx):
    """The price of ``cart`` without any offer."""
    return sum(catalog.unit_price(sku, ctx) * qty for sku, qty in cart.items())


def merge_lines(lines):
    """Merge the single-unit lines of the same SKU, for printing."""
    merged = []
    singles = {}
    for line in lines:
        if line["offer"]:
            merged.append(line)
            continue
        (sku, qty), = line["units"].items()
        if sku in singles:
            entry = singles[sku]
            entry["units"][sku] += qty
            entry["amount"] += line["amount"]
        else:
            entry = {"offer": "", "units": {sku: qty}, "amount": line["amount"]}
            singles[sku] = entry
            merged.append(entry)
    return merged
