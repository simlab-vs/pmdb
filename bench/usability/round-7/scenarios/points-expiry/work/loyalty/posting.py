"""Posting the day's activity from the POS and web-shop feeds.

Earn records carry base points; purchase points are multiplied by the
member's tier multiplier (rounded down). A burn takes points from the
member's lots, soonest to expire first. A burn larger than the balance is
rejected (the till checks the balance online, so this only happens when two
tills redeem at once). Positive adjustments are goodwill lots; negative ones
are taken like burns.
"""

import logging
from collections import Counter
from decimal import Decimal, ROUND_FLOOR

from . import audit, store
from .models import (
    ADJUST, BURN, EARN, GOODWILL, PURCHASE, Consumption,
    LEDGER_ADJUST, LEDGER_BURN, LEDGER_EARN,
)

log = logging.getLogger(__name__)


class PostingError(ValueError):
    pass


def earned_points(activity, tier, multipliers):
    if activity.source != PURCHASE:
        return activity.points
    multiplier = multipliers.get(tier, Decimal(1))
    return int((Decimal(activity.points) * multiplier).to_integral_value(rounding=ROUND_FLOOR))


def plan_consumption(lots, points):
    """Which lots a burn of ``points`` takes from; ``lots`` in consumption order."""
    plan, left = [], points
    for lot in lots:
        if not left:
            break
        take = min(lot.remaining, left)
        if take:
            plan.append(Consumption(lot.id, take))
            left -= take
    if left:
        return None
    return plan


def post_one(conn, activity, member, policy, multipliers, totals):
    if activity.kind == EARN:
        points = earned_points(activity, member.tier, multipliers)
        lot_id = store.insert_lot(conn, activity.member_id, activity.business_date, activity.source, points)
        store.insert_ledger(conn, member.id, activity.business_date, LEDGER_EARN, points, lot_id, audit.stamp())
        totals["earn_points"] += points
        return True
    if activity.kind == ADJUST and activity.points > 0:
        lot_id = store.insert_lot(conn, activity.member_id, activity.business_date, GOODWILL, activity.points)
        store.insert_ledger(conn, member.id, activity.business_date, LEDGER_ADJUST, activity.points, lot_id,
                            audit.stamp())
        totals["adjust_points"] += activity.points
        return True
    if activity.kind in (BURN, ADJUST):
        wanted = abs(activity.points)
        lots = policy.consumption_order(store.open_lots(conn, member.id))
        plan = plan_consumption(lots, wanted)
        if plan is None:
            return False
        kind = LEDGER_BURN if activity.kind == BURN else LEDGER_ADJUST
        for step in plan:
            store.take_from_lot(conn, step.lot_id, step.points)
            store.insert_ledger(conn, member.id, activity.business_date, kind, -step.points, step.lot_id,
                                audit.stamp())
        if activity.kind == BURN:
            totals["burn_points"] += wanted
        else:
            totals["adjust_points"] -= wanted
        return True
    raise PostingError(f"activity {activity.id}: unknown kind {activity.kind!r}")


def post_day(conn, business_date, members, policy, multipliers):
    """Post the pending activity of ``business_date``; returns the totals."""
    totals = Counter()
    for activity in store.pending_activity(conn, business_date):
        member = members.get(activity.member_id)
        if member is None:
            raise PostingError(f"activity {activity.id}: unknown member {activity.member_id}")
        with store.transaction(conn):
            if post_one(conn, activity, member, policy, multipliers, totals):
                store.mark_posted(conn, activity.id, audit.stamp())
                totals[activity.kind] += 1
            else:
                store.mark_rejected(conn, activity.id, audit.stamp())
                totals["rejected"] += 1
                log.info("rejected %s %s of %s: %d points exceed the balance",
                         activity.kind, activity.ref, activity.member_id, abs(activity.points))
    return totals
