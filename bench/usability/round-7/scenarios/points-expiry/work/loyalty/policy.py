"""Expiry rules of the terms and conditions (section 7).

- Points expire at the end of the twelfth calendar month after the month in
  which they were earned: points earned on 14 March 2025 expire at the end of
  31 March 2026. Promotional bonus points expire at the end of the third month,
  goodwill points like purchase points. The months per source are configured
  in ``[expiry.months]``.
- Expiry is booked by the nightly job on the last day of each month.
- Members of the exempt tiers (platinum) keep their points.
- Closed accounts forfeit their remaining points at the next month end.
"""

from . import clock, dates
from .models import CLOSED


class PolicyError(ValueError):
    pass


class ExpiryPolicy:
    def __init__(self, months_by_source, exempt_tiers):
        if not months_by_source:
            raise PolicyError("no expiry periods configured")
        for source, months in months_by_source.items():
            if not isinstance(months, int) or months < 1:
                raise PolicyError(f"expiry period of {source!r} must be a positive number of months")
        self.months_by_source = dict(months_by_source)
        self.exempt_tiers = frozenset(exempt_tiers)

    def months(self, source):
        months = self.months_by_source.get(source)
        if months is None:
            raise PolicyError(f"no expiry period for points of source {source!r}")
        return months

    def expiry_date(self, source, earned_on):
        """The last day on which points earned on ``earned_on`` are valid."""
        return dates.end_of_month(dates.add_months(dates.first_of_month(earned_on), self.months(source)))

    def expires_on(self, lot):
        return self.expiry_date(lot.source, lot.earned_on)

    def cutoff_for(self, source, on):
        """Points of ``source`` earned before the returned date have expired by
        the end of the month containing ``on``."""
        return dates.add_months(dates.first_of_month(on), 1 - self.months_by_source[source])

    def due_lots(self, lots, on=None):
        """Lots whose points expire at the end of the month containing ``on`` (default: today)."""
        on = on or clock.today()
        cutoffs = {source: self.cutoff_for(source, on) for source in self.months_by_source}
        return [lot for lot in lots if lot.earned_on < cutoffs[lot.source]]

    def exempt(self, member):
        return member.tier in self.exempt_tiers

    def forfeits(self, member):
        return member.status == CLOSED

    def earning_months(self, month_end):
        """For each source, the month (``YYYY-MM``) whose points expire at ``month_end``."""
        first = dates.first_of_month(month_end)
        return {
            source: dates.month_key(dates.add_months(first, -months))
            for source, months in self.months_by_source.items()
        }

    def points_expiring(self, lots, month_end):
        """Points of ``lots`` that expire at the end of the month ending ``month_end``."""
        months = self.earning_months(month_end)
        return sum(lot.remaining for lot in lots if lot.earned_on[:7] == months[lot.source])

    def consumption_order(self, lots):
        """Lots in the order burns consume them: soonest to expire first."""
        return sorted(lots, key=lambda lot: (self.expires_on(lot), lot.earned_on, lot.id))
