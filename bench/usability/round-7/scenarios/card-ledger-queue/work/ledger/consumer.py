"""Applying processor notifications to the card ledger."""

import logging
from collections import Counter

from . import fees, holds, mcc, parking, postings
from .fees import atm_fee, fx_fee
from .mcc import group_for
from .messages import AUTHORIZATION, CLEARING, REFUND, REVERSAL, TOPUP, KNOWN_TYPES
from .money import to_minor
from .timeutil import parse_ts

log = logging.getLogger(__name__)

stats = Counter()
_settings = None


def configure(settings):
    global _settings
    _settings = settings
    fees.configure(settings)
    mcc.configure(settings.mcc_groups)
    stats.clear()
    holds.reset()
    parking.reset()
    postings.reset()


def handle(message):
    """Apply one new notification. Returns what was done with it."""
    if message.programme != _settings.programme_id:
        stats["other_programme"] += 1
        return "skipped"
    if message.event_type not in KNOWN_TYPES:
        stats["unknown_type"] += 1
        log.debug("ignoring %s notification %s", message.event_type, message.event_id)
        return "skipped"
    stats[message.event_type] += 1
    if message.event_type == AUTHORIZATION:
        return on_authorization(message)
    if message.event_type == REVERSAL:
        return on_reversal(message)
    if message.event_type == CLEARING:
        return on_clearing(message)
    if message.event_type == REFUND:
        return on_refund(message)
    return on_topup(message)


def on_authorization(message):
    data = message.data
    when = parse_ts(data.get("transaction_time") or "1970-01-01")
    amount = to_minor(data["billing_amount"], _settings.currency)
    holds.open_hold(data["card"], data["auth_code"], amount, when)
    postings.touch(data["card"])
    for waiting in parking.take(data["card"], data["auth_code"]):
        if waiting.event_type == CLEARING:
            on_clearing(waiting)
        else:
            on_reversal(waiting)
    return "held"


def on_reversal(message):
    data = message.data
    if holds.find(data["card"], data["auth_code"]) is None:
        parking.park(message)
        return "parked"
    holds.release(data["card"], data["auth_code"])
    return "released"


def on_clearing(message):
    data = message.data
    auth_code = data.get("auth_code")
    if not auth_code:
        stats["offline"] += 1
        return post_clearing(message)
    if holds.find(data["card"], auth_code) is None:
        parking.park(message)
        return "parked"
    amount = to_minor(data["billing_amount"], _settings.currency)
    holds.consume(data["card"], auth_code, amount, data.get("final", True))
    return post_clearing(message)


def post_clearing(message):
    data = message.data
    merchant = data["merchant"]
    amount = to_minor(data["billing_amount"], _settings.currency)
    group = group_for(merchant.get("mcc", ""))
    ref = data["network_ref"]
    postings.post(postings.Posting(data["card"], postings.CLEARING, amount, group, ref))
    fee = fx_fee(data["currency"], amount)
    if fee:
        postings.post(postings.Posting(data["card"], postings.FX_FEE, fee, group, ref))
    fee = atm_fee(merchant.get("mcc", ""), merchant.get("country", ""))
    if fee:
        postings.post(postings.Posting(data["card"], postings.ATM_FEE, fee, group, ref))
    return "posted"


def on_refund(message):
    data = message.data
    amount = to_minor(data["billing_amount"], _settings.currency)
    group = group_for(data["merchant"].get("mcc", ""))
    postings.post(postings.Posting(data["card"], postings.REFUND, amount, group, data["network_ref"]))
    return "posted"


def on_topup(message):
    data = message.data
    amount = to_minor(data["amount"], data["currency"])
    if data["currency"] != _settings.currency:
        stats["topup_foreign"] += 1
        log.warning("top-up %s in %s ignored", data["topup_id"], data["currency"])
        return "skipped"
    postings.post(postings.Posting(data["card"], postings.TOPUP, amount, "", data["topup_id"]))
    return "posted"


def finish():
    """Handle what is still parked once the queue is drained."""
    late = Counter()
    for message in parking.leftovers():
        if message.event_type == CLEARING:
            post_clearing(message)
            late[CLEARING] += 1
        else:
            late[message.event_type] += 1
    return late
