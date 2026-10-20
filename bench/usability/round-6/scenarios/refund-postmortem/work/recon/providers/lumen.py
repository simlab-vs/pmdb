"""Lumen.

Lumen sends notifications in the presentment currency and settles in EUR at
the reference rate of the notification's day. Processing fees are reported
in EUR. Notifications:

* ``AUTHORISATION`` with ``success`` ``"true"`` or ``"false"``;
* ``REFUND`` for ``originalReference``;
* ``CHARGEBACK`` and ``CHARGEBACK_REVERSED``.

Other event codes (reports, account updates) carry no money.
"""

from ..models import Txn, CHARGE, REFUND, DISPUTE, OTHER, SUCCEEDED, FAILED

KIND_BY_CODE = {
    "AUTHORISATION": CHARGE,
    "REFUND": REFUND,
    "CHARGEBACK": DISPUTE,
    "CHARGEBACK_REVERSED": DISPUTE,
}


def normalize(raw, fx):
    body = raw.body
    code = body.get("eventCode", "")
    kind = KIND_BY_CODE.get(code, OTHER)
    money = body.get("amount") or {"value": 0, "currency": "EUR"}
    currency = money["currency"].upper()
    amount = int(money["value"])
    settle = fx.convert(amount, currency, raw.ts) if amount else 0
    if code == "CHARGEBACK_REVERSED":
        settle = -settle
    fee = body.get("fees") or {"value": 0}
    status = SUCCEEDED if str(body.get("success", "true")).lower() == "true" else FAILED
    return Txn(
        provider="lumen",
        kind=kind,
        ref=body.get("pspReference", raw.event_id),
        parent=body.get("originalReference"),
        account=body.get("merchantAccount", ""),
        ts=raw.ts,
        currency=currency,
        amount=amount,
        settle_amount=settle,
        fee=int(fee["value"]),
        status=status,
        event_id=raw.event_id,
    )
