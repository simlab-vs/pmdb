"""Allocation policy: how much of a warehouse's stock a line may take.

Each warehouse keeps a safety stock per SKU (planned by replenishment) so
that our own shop and B2B customers can still be served when a SKU runs
low. Lines of the protected channels (``protect_safety_stock_from`` in
the settings) may only take the stock above it.
"""

from . import ledger

_protected = frozenset()


def configure(settings):
    global _protected
    _protected = frozenset(settings.protected_channels)


def protected(channel):
    return channel in _protected


def allocatable(sku, warehouse, channel):
    """Units of ``sku`` that ``warehouse`` can give a line of ``channel``."""
    free = ledger.remaining(sku, warehouse)
    if protected(channel):
        free -= ledger.safety_stock(sku, warehouse)
    return free
