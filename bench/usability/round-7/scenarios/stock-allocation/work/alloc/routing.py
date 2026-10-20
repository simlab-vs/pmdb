"""Which warehouses may ship a line, in order of preference.

Each destination country has a configured sequence of warehouses, nearest
first. A warehouse is skipped if it can't handle the product (hazardous
goods need a licence, bulky goods a bulky-goods dock) or doesn't stock it.
"""

from . import catalog, ledger

_warehouses = {}
_routes = {}
_default = ()


def configure(settings):
    global _default
    _warehouses.clear()
    _warehouses.update(settings.warehouses)
    _routes.clear()
    _routes.update(settings.routes)
    _default = settings.default_route


def route(country):
    return _routes.get(country, _default)


def can_handle(warehouse, sku):
    spec = _warehouses[warehouse]
    attributes = catalog.attributes(sku)
    if attributes.hazmat and not spec.hazmat:
        return False
    if attributes.bulky and not spec.bulky:
        return False
    return True


def sources_for(line):
    """Warehouses that may ship ``line``, in order of preference."""
    if catalog.is_kit(line.sku):
        parts = [component for component, _ in catalog.components(line.sku)]
    else:
        parts = [line.sku]
    sources = []
    for warehouse in route(line.country):
        if all(can_handle(warehouse, part) and ledger.stocks(part, warehouse) for part in parts):
            sources.append(warehouse)
    return sources
