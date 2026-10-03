"""Kestrel Payments.

Kestrel settles in EUR and sends every amount in EUR minor units. Events:

* ``charge``: a card payment, ``data.status`` is ``succeeded`` or ``failed``;
  ``data.fee`` is the processing fee.
* ``refund``: money returned to the customer for ``data.charge``.
* ``dispute``: funds withdrawn for a chargeback.
* ``dispute_reversal``: funds reinstated after a won chargeback.
"""

from ..models import Txn, CHARGE, REFUND, DISPUTE, OTHER, SUCCEEDED

KIND_BY_TYPE = {
    "charge": CHARGE,
    "refund": REFUND,
    "dispute": DISPUTE,
    "dispute_reversal": DISPUTE,
}


def normalize(raw, fx):
    body = raw.body
    data = body.get("data", {})
    kind = KIND_BY_TYPE.get(body["type"], OTHER)
    amount = int(data.get("amount", 0))
    settle = amount
    if body["type"] == "dispute_reversal":
        settle = -amount
    return Txn(
        provider="kestrel",
        kind=kind,
        ref=data.get("id", raw.event_id),
        parent=data.get("charge"),
        account=body.get("account", ""),
        ts=raw.ts,
        currency=data.get("currency", "eur").upper(),
        amount=amount,
        settle_amount=settle,
        fee=int(data.get("fee", 0)),
        status=data.get("status", SUCCEEDED),
        event_id=raw.event_id,
    )
