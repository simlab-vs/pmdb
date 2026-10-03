"""Records passed between the stages of the allocation run."""

from typing import NamedTuple

WEB = "web"
MARKETPLACE = "marketplace"
B2B = "b2b"
CHANNELS = (WEB, MARKETPLACE, B2B)

EXPRESS = "express"
STANDARD = "standard"


class OrderLine(NamedTuple):
    """One open order line, as exported by the OMS."""

    order_id: str
    line_no: int
    sku: str
    qty: int
    channel: str
    service: str
    country: str
    created_at: str
    ship_complete: bool


class Level(NamedTuple):
    """Stock of one SKU in one warehouse, as reported by the inventory service.

    ``available`` is what can still be promised: on hand minus what is
    already reserved for orders in picking, never below zero.
    """

    sku: str
    warehouse: str
    on_hand: int
    reserved: int
    available: int
    safety_stock: int
    bin: str
    status: str


class Pick(NamedTuple):
    warehouse: str
    sku: str
    qty: int


class Allocation(NamedTuple):
    """The outcome for one order line: where it ships from, and what waits."""

    order_id: str
    line_no: int
    sku: str
    channel: str
    service: str
    ordered: int
    picks: tuple
    backordered: int
    reason: str


class PickRow(NamedTuple):
    wave: str
    order_id: str
    line_no: int
    sku: str
    bin: str
    qty: int
