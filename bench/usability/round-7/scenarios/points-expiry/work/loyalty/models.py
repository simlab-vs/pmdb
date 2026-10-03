"""Records of the points database, as read by the job."""

from typing import NamedTuple

# Member status
ACTIVE = "active"
CLOSED = "closed"

# Activity kinds (from the POS / e-commerce feeds)
EARN = "earn"
BURN = "burn"
ADJUST = "adjust"

# Lot sources
PURCHASE = "purchase"
PROMO = "promo"
GOODWILL = "goodwill"

# Ledger entry kinds
LEDGER_EARN = "earn"
LEDGER_BURN = "burn"
LEDGER_EXPIRE = "expire"
LEDGER_FORFEIT = "forfeit"
LEDGER_ADJUST = "adjust"

TIERS = ("basic", "silver", "gold", "platinum")


class Member(NamedTuple):
    id: str
    tier: str
    status: str
    joined_on: str
    opt_in: bool


class Lot(NamedTuple):
    """Points earned together, consumed oldest-expiring first."""

    id: int
    member_id: str
    earned_on: str
    source: str
    points: int
    remaining: int


class Activity(NamedTuple):
    id: int
    member_id: str
    business_date: str
    kind: str
    source: str
    points: int
    ref: str


class Consumption(NamedTuple):
    lot_id: int
    points: int
