"""Shipping charges."""

PARCEL_LIMIT_UNITS = 30


def shipping_charge(subtotal, units, ctx, region):
    """The shipping charge for a quote of ``units`` units worth ``subtotal``.

    Store orders are collected in the store.  Trade customers and orders of
    at least the region's threshold ship for free.  Orders too large for one
    parcel pay the fee once per parcel.
    """
    if ctx.channel == "store":
        return 0
    if ctx.tier == "trade" or subtotal >= region.free_shipping_from:
        return 0
    parcels = 1 + (units - 1) // PARCEL_LIMIT_UNITS
    return parcels * region.shipping_fee
