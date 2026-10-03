"""Recognising notifications we have already processed.

Delivery is at least once on two levels:

- the queue redelivers a message whose visibility timeout ran out before we
  acknowledged it: same ``MessageId``, same body;
- the processor re-sends a notification our endpoint didn't acknowledge in
  time: a new queue message with a new ``event_id`` (event ids identify a
  delivery attempt), and otherwise the same event.

Redeliveries are recognised by their message id. Re-sends are recognised by
the transaction they describe: the fields that identify a card transaction
for the scheme (card, amount and currency, merchant, transaction time and
authorization code), which the processor copies unchanged into every
attempt.

The state lives for one run (one business date): the processor gives up
re-sending after six hours, and the queue's retention is four days, so the
job is run once the day's traffic has drained.
"""

from collections import Counter

NEW = "new"
REDELIVERY = "redelivery"
RESEND = "resend"

IDENTITY_FIELDS = ("card", "amount", "currency", "transaction_time", "auth_code")

_message_ids = set()
_fingerprints = {}
stats = Counter()


def reset():
    _message_ids.clear()
    _fingerprints.clear()
    stats.clear()


def fingerprint(message):
    """The identity of the card event a notification describes."""
    data = message.data
    merchant = data.get("merchant") or {}
    return (message.event_type, merchant.get("id")) + tuple(
        data.get(field) for field in IDENTITY_FIELDS
    )


def classify(message):
    """Return NEW the first time an event is seen, else why it is a repeat."""
    if message.message_id in _message_ids:
        stats[REDELIVERY] += 1
        return REDELIVERY
    _message_ids.add(message.message_id)
    key = fingerprint(message)
    first = _fingerprints.get(key)
    if first is not None:
        stats[RESEND] += 1
        stats[f"{RESEND}.{message.event_type}"] += 1
        return RESEND
    _fingerprints[key] = message.event_id
    stats[NEW] += 1
    return NEW
