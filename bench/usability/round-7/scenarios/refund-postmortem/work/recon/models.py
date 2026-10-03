"""Normalized transaction model shared by the provider adapters and the ledger."""

from typing import NamedTuple, Optional

CHARGE = "charge"
REFUND = "refund"
DISPUTE = "dispute"
OTHER = "other"

KINDS = (CHARGE, REFUND, DISPUTE, OTHER)

SUCCEEDED = "succeeded"
PENDING = "pending"
FAILED = "failed"
CANCELED = "canceled"


class Txn(NamedTuple):
    """One provider event, normalized.

    Amounts are integers in minor units. ``amount`` is in the presentment
    currency ``currency``; ``settle_amount`` and ``fee`` are in the settlement
    currency of the job (EUR). For disputes ``settle_amount`` is positive for
    funds withdrawn from the balance and negative for funds reinstated.
    """

    provider: str
    kind: str
    ref: str
    parent: Optional[str]
    account: str
    ts: int
    currency: str
    amount: int
    settle_amount: int
    fee: int
    status: str
    event_id: str


class RawEvent(NamedTuple):
    """An event as read from the export, before provider-specific parsing."""

    provider: str
    event_id: str
    ts: int
    body: dict
