"""Job settings (config/settings.toml)."""

import tomllib
from typing import NamedTuple

from .money import to_minor


class Settings(NamedTuple):
    programme: str
    programme_id: str
    currency: str
    queue_url: str
    receive_batch: int
    out_dir: str
    fx_fee_bp: int
    atm_fee: int
    atm_fee_free_country: str
    mcc_groups: dict


def load_settings(path):
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    job = raw["job"]
    fees = raw.get("fees", {})
    groups = {}
    for group, codes in raw.get("mcc_groups", {}).items():
        for code in codes:
            groups[str(code)] = group
    return Settings(
        programme=job["programme"],
        programme_id=job["programme_id"],
        currency=job.get("currency", "EUR"),
        queue_url=job["queue_url"],
        receive_batch=int(job.get("receive_batch", 10)),
        out_dir=job.get("out_dir", "reports"),
        fx_fee_bp=int(fees.get("fx_fee_bp", 0)),
        atm_fee=to_minor(fees.get("atm_fee", "0"), job.get("currency", "EUR")),
        atm_fee_free_country=fees.get("atm_fee_free_country", ""),
        mcc_groups=groups,
    )
