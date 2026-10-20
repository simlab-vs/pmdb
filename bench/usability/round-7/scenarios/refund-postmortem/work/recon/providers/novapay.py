"""NovaPay.

NovaPay settles in EUR. Events carry the affected object in
``data.object``; ``type`` is ``charge``, ``refund`` or ``dispute``.

Accounts on API version 2026-08-01 and later send amounts as decimal strings
(``"12.50"``) and the fee as ``fee_details.amount``; older accounts send
integer minor units and ``fee``.
"""

from ..models import Txn, CHARGE, REFUND, DISPUTE, OTHER, SUCCEEDED
from ..money import to_minor

KIND_BY_TYPE = {
    "charge": CHARGE,
    "refund": REFUND,
    "dispute": DISPUTE,
}


def object_fee(obj, currency):
    details = obj.get("fee_details")
    if details is not None:
        return to_minor(details.get("amount", "0"), currency)
    return to_minor(obj.get("fee", 0), currency)


def normalize(raw, fx):
    body = raw.body
    obj = body.get("data", {}).get("object", {})
    kind = KIND_BY_TYPE.get(body.get("type"), OTHER)
    currency = obj.get("currency", "EUR").upper()
    amount = to_minor(obj.get("amount", 0), currency)
    settle = fx.convert(amount, currency, raw.ts) if amount else 0
    if kind == DISPUTE and obj.get("direction") == "reinstatement":
        settle = -settle
    return Txn(
        provider="novapay",
        kind=kind,
        ref=obj.get("id", raw.event_id),
        parent=obj.get("charge"),
        account=body.get("account", ""),
        ts=raw.ts,
        currency=currency,
        amount=amount,
        settle_amount=settle,
        fee=object_fee(obj, currency),
        status=obj.get("status", SUCCEEDED),
        event_id=raw.event_id,
    )
