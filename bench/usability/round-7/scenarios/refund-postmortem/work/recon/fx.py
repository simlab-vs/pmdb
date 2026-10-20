"""Daily reference exchange rates into the settlement currency."""

import csv
import functools
import logging
from decimal import Decimal

from .money import minor_digits, round_minor
from .timeutil import day_of

log = logging.getLogger(__name__)


class FxError(LookupError):
    pass


class FxTable:
    """Rates quoted as units of foreign currency per one unit of the base."""

    def __init__(self, base, rates):
        self._cached_rate = functools.lru_cache(maxsize=None)(self._find_rate)
        self.base = base
        self.rates = rates
        self.lookups = 0
        self.fallbacks = 0

    @classmethod
    def load(cls, path, base="EUR"):
        rates = {}
        with open(path, newline="") as handle:
            for row in csv.DictReader(handle):
                rates[(row["date"], row["currency"].upper())] = Decimal(row["rate"])
        log.info("loaded %d FX rates from %s", len(rates), path)
        return cls(base, rates)

    def rate(self, currency, day):
        """Rate of ``currency`` on ``day``, falling back to the latest earlier day."""
        self.lookups += 1
        return self._cached_rate(currency, day)

    def _find_rate(self, currency, day):
        key = (day, currency)
        if key in self.rates:
            return self.rates[key]
        earlier = sorted(d for (d, c) in self.rates if c == currency and d < day)
        if not earlier:
            raise FxError(f"no {currency} rate on or before {day}")
        self.fallbacks += 1
        return self.rates[(earlier[-1], currency)]

    def convert(self, minor, currency, ts):
        """Convert ``minor`` units of ``currency`` at ``ts`` into base minor units."""
        currency = currency.upper()
        if currency == self.base:
            return minor
        rate = self.rate(currency, day_of(ts))
        shift = minor_digits(self.base) - minor_digits(currency)
        return round_minor(Decimal(minor).scaleb(shift) / rate)
