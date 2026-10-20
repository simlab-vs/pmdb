"""Tariffs: standing charges, tiered unit rates, levies and VAT."""

import json
import logging
from typing import NamedTuple

log = logging.getLogger(__name__)


class Tier(NamedTuple):
    """Unit rate for consumption up to ``limit`` kWh a month (None: no limit)."""

    limit: float
    rate: float


class Tariff(NamedTuple):
    code: str
    description: str
    standing_per_day: float
    tiers: list
    levy_per_kwh: float
    vat_rate: float


class TariffError(ValueError):
    """A tariff definition is inconsistent."""


def _parse_tiers(code, raw):
    tiers = []
    previous = 0.0
    for index, item in enumerate(raw):
        limit = item.get("up_to_kwh")
        if limit is None and index != len(raw) - 1:
            raise TariffError(f"{code}: only the last tier may be unlimited")
        if limit is not None and limit <= previous:
            raise TariffError(f"{code}: tier limits must increase")
        tiers.append(Tier(limit, float(item["rate"])))
        previous = limit if limit is not None else previous
    if not tiers or tiers[-1].limit is not None:
        raise TariffError(f"{code}: the last tier must be unlimited")
    return tiers


def load_tariffs(path):
    """Read ``tariffs.json`` into tariffs by code."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    tariffs = {}
    for code, spec in raw["tariffs"].items():
        tariffs[code] = Tariff(
            code=code,
            description=spec["description"],
            standing_per_day=float(spec["standing_charge_per_day"]),
            tiers=_parse_tiers(code, spec["tiers"]),
            levy_per_kwh=float(spec.get("levy_per_kwh", 0.0)),
            vat_rate=float(spec["vat_rate"]),
        )
    log.info("tariffs: %s", ", ".join(sorted(tariffs)))
    return tariffs


def scaled_tiers(tiers, fraction):
    """Tier limits for a part of a month: the limits shrink with the days."""
    if fraction >= 1:
        return list(tiers)
    return [Tier(None if tier.limit is None else tier.limit * fraction, tier.rate) for tier in tiers]


def energy_bands(kwh, tiers):
    """Split ``kwh`` over ``tiers``: a list of (kWh, rate) bands."""
    bands = []
    remaining = kwh
    floor = 0.0
    for tier in tiers:
        if remaining <= 0:
            break
        width = remaining if tier.limit is None else min(remaining, tier.limit - floor)
        if width > 0:
            bands.append((round(width, 3), tier.rate))
            remaining -= width
        if tier.limit is not None:
            floor = tier.limit
    return bands
