"""Job settings (config/settings.toml)."""

import tomllib
from typing import NamedTuple


class Warehouse(NamedTuple):
    code: str
    name: str
    country: str
    hazmat: bool
    bulky: bool
    express_cutoff: str


class Settings(NamedTuple):
    inventory_url: str
    inventory_timeout: float
    inventory_page_size: int
    warehouses: dict
    routes: dict
    default_route: tuple
    protected_channels: frozenset
    express_first: bool
    wave_size: int
    out_dir: str
    report_dir: str
    catalog_dir: str


class SettingsError(ValueError):
    pass


def load_settings(path):
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    job = raw.get("job", {})
    inventory = raw.get("inventory", {})
    warehouses = {}
    for code, spec in raw.get("warehouses", {}).items():
        warehouses[code] = Warehouse(
            code=code,
            name=spec["name"],
            country=spec["country"],
            hazmat=bool(spec.get("hazmat", False)),
            bulky=bool(spec.get("bulky", True)),
            express_cutoff=spec.get("express_cutoff", "14:00"),
        )
    routing = raw.get("routing", {})
    routes = {}
    for countries, sequence in routing.get("routes", {}).items():
        for country in countries.split(","):
            routes[country.strip().upper()] = tuple(sequence)
    default_route = tuple(routing.get("default", ()))
    for sequence in list(routes.values()) + [default_route]:
        for code in sequence:
            if code not in warehouses:
                raise SettingsError(f"route names unknown warehouse {code}")
    policy = raw.get("policy", {})
    return Settings(
        inventory_url=inventory.get("url", ""),
        inventory_timeout=float(inventory.get("timeout", 30)),
        inventory_page_size=int(inventory.get("page_size", 500)),
        warehouses=warehouses,
        routes=routes,
        default_route=default_route,
        protected_channels=frozenset(policy.get("protect_safety_stock_from", ())),
        express_first=bool(policy.get("express_first", True)),
        wave_size=int(job.get("wave_size", 40)),
        out_dir=job.get("out_dir", "out"),
        report_dir=job.get("report_dir", "reports"),
        catalog_dir=job.get("catalog_dir", "catalog"),
    )
