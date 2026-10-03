"""Points liability for finance.

Outstanding points are valued at the programme's point value, less the
expected breakage (points that will never be redeemed), as agreed with the
auditors. Points of closed accounts are reported separately: they are
forfeited at the next month end.
"""

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from . import dates, store
from .models import CLOSED, TIERS

CENT = Decimal("0.01")


def value_eur(points, point_value, breakage_rate):
    return (Decimal(points) * point_value * (1 - breakage_rate)).quantize(CENT, rounding=ROUND_HALF_UP)


def summarize(conn, business_date, policy, point_value, breakage_rate):
    by_tier = Counter({tier: 0 for tier in TIERS})
    by_source = Counter()
    closed_points = 0
    expiring = 0
    next_end = dates.next_month_end(business_date)
    for tier, status, source, earned_on, remaining in store.open_points_by_earning(conn):
        if status == CLOSED:
            closed_points += remaining
            continue
        by_tier[tier] += remaining
        by_source[source] += remaining
        if tier not in policy.exempt_tiers and policy.expiry_date(source, earned_on) == next_end:
            expiring += remaining
    outstanding = sum(by_tier.values())
    return {
        "outstanding_points": outstanding,
        "outstanding_by_tier": dict(by_tier),
        "outstanding_by_source": dict(sorted(by_source.items())),
        "closed_accounts_points": closed_points,
        "expiring_next_month": {"on": next_end, "points": expiring},
        "point_value_eur": str(point_value),
        "breakage_rate": str(breakage_rate),
        "value_eur": str(value_eur(outstanding, point_value, breakage_rate)),
    }
