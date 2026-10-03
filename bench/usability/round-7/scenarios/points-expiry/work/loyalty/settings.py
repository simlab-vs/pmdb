"""Job settings (``config/loyalty.toml``)."""

import tomllib
from decimal import Decimal
from typing import NamedTuple


class Settings(NamedTuple):
    programme: str
    timezone: str
    point_value_eur: Decimal
    breakage_rate: Decimal
    expiry_months: dict
    exempt_tiers: tuple
    tier_multipliers: dict
    batch_size: int
    crm_endpoint: str
    crm_timeout_s: float
    crm_retries: int
    report_dir: str


def load_settings(path):
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    programme = raw["programme"]
    expiry = raw["expiry"]
    crm = raw["crm"]
    return Settings(
        programme=programme["name"],
        timezone=programme["timezone"],
        point_value_eur=Decimal(programme["point_value_eur"]),
        breakage_rate=Decimal(programme["breakage_rate"]),
        expiry_months=dict(expiry["months"]),
        exempt_tiers=tuple(expiry.get("exempt_tiers", ())),
        tier_multipliers={k: Decimal(v) for k, v in raw["earning"]["tier_multipliers"].items()},
        batch_size=int(expiry.get("batch_size", 250)),
        crm_endpoint=crm["endpoint"],
        crm_timeout_s=float(crm.get("timeout_s", 10)),
        crm_retries=int(crm.get("retries", 3)),
        report_dir=raw["paths"]["report_dir"],
    )
