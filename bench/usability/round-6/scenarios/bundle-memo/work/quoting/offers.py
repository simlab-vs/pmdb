"""Bundle offers.

Three kinds of offers are supported:

``mix``
    Buy ``buy`` units from a product group, the ``free`` cheapest of them
    are free ("3 for 2 on loose teas").
``combo``
    A fixed set of units for a fixed price, set per price list
    ("Brewing kit: kettle and two cups").
``bulk``
    ``qty`` units of one SKU at ``percent`` % off.

An offer can be limited to channels, tiers and a date range.  Every unit
of a cart belongs to at most one offer.
"""

import itertools
import json
from typing import NamedTuple

from . import catalog
from .cart import contains, expand
from .money import apply_discount

KINDS = ("mix", "combo", "bulk")


class Offer(NamedTuple):
    id: str
    kind: str
    group: str
    buy: int
    free: int
    items: dict
    sku: str
    qty: int
    percent: str
    channels: tuple
    tiers: tuple
    valid_from: str
    valid_to: str


class Application(NamedTuple):
    """One use of an offer: the units it takes and what they cost."""

    offer: str
    take: dict
    amount: int


class OfferError(ValueError):
    """An offer in ``offers.json`` is malformed."""


def _offer(raw):
    kind = raw.get("kind")
    if kind not in KINDS:
        raise OfferError(f"offer {raw.get('id')!r}: unknown kind {kind!r}")
    offer = Offer(
        id=raw["id"],
        kind=kind,
        group=raw.get("group", ""),
        buy=int(raw.get("buy", 0)),
        free=int(raw.get("free", 0)),
        items={k.upper(): int(v) for k, v in raw.get("items", {}).items()},
        sku=raw.get("sku", "").upper(),
        qty=int(raw.get("qty", 0)),
        percent=str(raw.get("percent", "0")),
        channels=tuple(raw.get("channels") or ()),
        tiers=tuple(raw.get("tiers") or ()),
        valid_from=raw.get("from", "0000-01-01"),
        valid_to=raw.get("to", "9999-12-31"),
    )
    if kind == "mix" and not (offer.group and 0 < offer.free < offer.buy):
        raise OfferError(f"offer {offer.id}: a mix offer needs a group and 0 < free < buy")
    if kind == "combo" and len(offer.items) < 2 and sum(offer.items.values()) < 2:
        raise OfferError(f"offer {offer.id}: a combo needs at least two units")
    if kind == "bulk" and (not offer.sku or offer.qty < 2):
        raise OfferError(f"offer {offer.id}: a bulk offer needs a SKU and qty >= 2")
    return offer


def load_offers(path):
    """Read ``offers.json`` and return the offers, in file order."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    offers = [_offer(entry) for entry in raw["offers"]]
    ids = [o.id for o in offers]
    if len(ids) != len(set(ids)):
        raise OfferError("duplicate offer ids")
    return offers


def eligible(offer, ctx):
    """Whether ``offer`` can be used in the pricing context ``ctx``."""
    if offer.channels and ctx.channel not in offer.channels:
        return False
    if offer.tiers and ctx.tier not in offer.tiers:
        return False
    return offer.valid_from <= ctx.date <= offer.valid_to


def eligible_offers(offers, ctx):
    return [o for o in offers if eligible(o, ctx)]


def offer_skus(offer):
    """The SKUs whose units ``offer`` can take."""
    if offer.kind == "mix":
        return catalog.group_members(offer.group)
    if offer.kind == "combo":
        return sorted(offer.items)
    return [offer.sku]


def index_by_sku(offers):
    """A dict from each SKU to the offers that can take its units."""
    by_sku = {}
    for offer in offers:
        for sku in offer_skus(offer):
            by_sku.setdefault(sku, []).append(offer)
    return by_sku


def _mix_applications(offer, cart, sku, ctx):
    if not catalog.in_group(sku, offer.group):
        return []
    price = {s: catalog.unit_price(s, ctx) for s in cart if catalog.in_group(s, offer.group)}
    pool = expand(cart, price)
    pool.remove(sku)
    seen = set()
    result = []
    for others in itertools.combinations(pool, offer.buy - 1):
        if others in seen:
            continue
        seen.add(others)
        chosen = (sku,) + others
        amount = sum(sorted(price[s] for s in chosen)[offer.free:])
        take = {}
        for s in chosen:
            take[s] = take.get(s, 0) + 1
        result.append(Application(offer.id, take, amount))
    return result


def _combo_applications(offer, cart, sku, ctx):
    if sku not in offer.items or not contains(cart, offer.items):
        return []
    price = catalog.combo_price(offer.id, ctx)
    if price is None:
        return []
    return [Application(offer.id, dict(offer.items), price)]


def _bulk_applications(offer, cart, sku, ctx):
    if sku != offer.sku or cart.get(sku, 0) < offer.qty:
        return []
    amount = apply_discount(offer.qty * catalog.unit_price(sku, ctx), offer.percent)
    return [Application(offer.id, {sku: offer.qty}, amount)]


_APPLY = {
    "mix": _mix_applications,
    "combo": _combo_applications,
    "bulk": _bulk_applications,
}


def offer_applications(offer, cart, sku, ctx):
    """Every way to use ``offer`` on units of ``cart`` including ``sku``."""
    return _APPLY[offer.kind](offer, cart, sku, ctx)
