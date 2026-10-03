"""Job settings, read from ``config/settings.toml``."""

import tomllib
from pathlib import Path
from typing import NamedTuple


class Settings(NamedTuple):
    settlement_currency: str
    providers: tuple
    ignored_statuses: tuple
    fx_dir: str
    report_dir: str


DEFAULTS = {
    "settlement_currency": "EUR",
    "providers": ("kestrel", "lumen", "novapay"),
    "ignored_statuses": ("failed", "canceled"),
    "fx_dir": "config/fx",
    "report_dir": "reports",
}


def load_settings(path):
    """Load settings, filling in defaults for missing keys."""
    values = dict(DEFAULTS)
    path = Path(path)
    if path.exists():
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        job = data.get("job", {})
        for key in DEFAULTS:
            if key in job:
                value = job[key]
                values[key] = tuple(value) if isinstance(value, list) else value
    return Settings(**values)
