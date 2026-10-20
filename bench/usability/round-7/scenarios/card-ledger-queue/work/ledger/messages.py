"""Processor notifications, as received from the queue.

The card processor sends one notification per card event. The queue message
body is the processor's envelope::

    {"event_id": "evt_…", "type": "clearing", "created": "2026-09-28T14:03:11Z",
     "programme": "KPE-01", "data": {…}}

``event_id`` identifies the notification: the processor creates a new one
for every delivery attempt it makes, and re-sends a notification when our
endpoint didn't acknowledge it in time.

``data`` by type:

- ``authorization``: ``auth_code``, ``card``, ``amount``/``currency`` (as the
  merchant asked), ``billing_amount`` (programme currency), ``merchant``
  (``id``, ``name``, ``mcc``, ``country``), ``transaction_time``.
- ``authorization.reversal``: the authorization's ``auth_code``, ``card``,
  ``amount``, ``currency``, ``billing_amount``, ``merchant`` and the
  reversal's ``transaction_time``.
- ``clearing``: the presentment of a transaction by the acquirer:
  ``network_ref`` (the network's reference of the presentment),
  ``auth_code`` (absent for offline transactions), ``card``, ``amount``,
  ``currency``, ``billing_amount``, ``merchant``, ``transaction_time``, and
  ``final`` (false when the merchant will present more of the
  authorization, e.g. split shipments).
- ``refund``: like a clearing, money back to the card.
- ``topup``: ``topup_id``, ``card``, ``amount``, ``currency``, ``source``
  (``sepa``, ``card``, ``voucher``), ``transaction_time``.
"""

import json
from typing import NamedTuple

from .timeutil import from_millis

AUTHORIZATION = "authorization"
REVERSAL = "authorization.reversal"
CLEARING = "clearing"
REFUND = "refund"
TOPUP = "topup"

KNOWN_TYPES = (AUTHORIZATION, REVERSAL, CLEARING, REFUND, TOPUP)

REQUIRED = {
    AUTHORIZATION: ("auth_code", "card", "amount", "currency", "billing_amount", "merchant"),
    REVERSAL: ("auth_code", "card", "billing_amount"),
    CLEARING: ("network_ref", "card", "amount", "currency", "billing_amount", "merchant"),
    REFUND: ("network_ref", "card", "amount", "currency", "billing_amount", "merchant"),
    TOPUP: ("topup_id", "card", "amount", "currency"),
}


class MessageError(ValueError):
    pass


class Message(NamedTuple):
    message_id: str
    receive_count: int
    sent_at: int
    event_id: str
    event_type: str
    programme: str
    data: dict


def parse_message(raw):
    """Turn a received queue message into a ``Message``."""
    try:
        body = json.loads(raw["Body"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise MessageError(f"message {raw.get('MessageId')}: unreadable body ({exc})") from exc
    attributes = raw.get("Attributes", {})
    event_type = body.get("type", "")
    data = body.get("data") or {}
    for field in REQUIRED.get(event_type, ()):
        if field not in data:
            raise MessageError(f"message {raw['MessageId']}: {event_type} without {field}")
    return Message(
        message_id=raw["MessageId"],
        receive_count=int(attributes.get("ApproximateReceiveCount", 1)),
        sent_at=from_millis(attributes.get("SentTimestamp", 0)),
        event_id=body.get("event_id", ""),
        event_type=event_type,
        programme=body.get("programme", ""),
        data=data,
    )

