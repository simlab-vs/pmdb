"""Estimated consumption for accounts without usable readings."""

import logging

log = logging.getLogger(__name__)

_DOMESTIC_PROFILE = {
    1: 1.31, 2: 1.18, 3: 1.07, 4: 0.94, 5: 0.86, 6: 0.79,
    7: 0.78, 8: 0.80, 9: 0.87, 10: 1.00, 11: 1.15, 12: 1.25,
}
_BUSINESS_PROFILE = {
    1: 1.12, 2: 1.08, 3: 1.04, 4: 0.98, 5: 0.95, 6: 0.93,
    7: 0.92, 8: 0.88, 9: 0.97, 10: 1.01, 11: 1.05, 12: 1.07,
}


def seasonal_factor(segment, month):
    profile = _BUSINESS_PROFILE if segment == "business" else _DOMESTIC_PROFILE
    return profile[month] / (sum(profile.values()) / 12)


def estimate_consumption(account, period, days):
    """kWh for ``days`` of ``period`` from the account's annual estimate."""
    if account.eac <= 0:
        log.warning("account %s has no annual consumption estimate", account.account)
        return 0.0
    month = int(period.label[5:7])
    daily = account.eac / 365 * seasonal_factor(account.segment, month)
    return round(daily * days, 1)
