"""Monthly points statements.

At month end every member with an open account gets a statement: the
month's movements, the closing balance and the points that will expire at
the end of the next month. The CRM renders and e-mails them (to members
who opted in) and shows them in the app.
"""

from . import clock, dates, store
from .models import LEDGER_ADJUST, LEDGER_BURN, LEDGER_EARN, LEDGER_EXPIRE, LEDGER_FORFEIT


def statement(member, lots, movements, policy, business_date):
    closing = sum(lot.remaining for lot in lots)
    earned = movements.get(LEDGER_EARN, 0)
    burned = -movements.get(LEDGER_BURN, 0)
    adjusted = movements.get(LEDGER_ADJUST, 0)
    expired = -movements.get(LEDGER_EXPIRE, 0) - movements.get(LEDGER_FORFEIT, 0)
    opening = closing - earned + burned - adjusted + expired
    next_end = dates.next_month_end(business_date)
    expiring = 0 if policy.exempt(member) else policy.points_expiring(lots, next_end)
    return {
        "member_id": member.id,
        "month": dates.month_key(business_date),
        "tier": member.tier,
        "opening": opening,
        "earned": earned,
        "redeemed": burned,
        "adjusted": adjusted,
        "expired": expired,
        "closing": closing,
        "expiring": {"points": expiring, "on": next_end},
        "email": member.opt_in,
        "generated_at": clock.stamp(),
    }


def statements_for(conn, batch, policy, business_date):
    """Statements of a batch of members, after the batch's expiry was booked."""
    ids = [member.id for member in batch]
    lots = store.open_lots_of(conn, ids)
    first, last = dates.month_range(business_date)
    movements = store.month_movements(conn, ids, first, last)
    result = []
    for member in batch:
        if policy.forfeits(member):
            continue
        result.append(statement(member, lots[member.id], movements[member.id], policy, business_date))
    return result
