"""Merchant category codes and the report's groups."""

OTHER_GROUP = "other"

CASH_MCCS = frozenset({"6010", "6011"})

DESCRIPTIONS = {
    "4111": "commuter transport",
    "4121": "taxis",
    "4131": "bus lines",
    "4784": "tolls and bridge fees",
    "5411": "grocery stores",
    "5541": "service stations",
    "5542": "automated fuel dispensers",
    "5812": "restaurants",
    "5814": "fast food",
    "6011": "ATM cash",
    "7011": "hotels",
    "7523": "parking",
}


_groups = {}


def configure(groups):
    """Install the report's merchant groups (MCC -> group) from the settings."""
    _groups.clear()
    _groups.update(groups)


def group_for(mcc):
    return _groups.get(str(mcc), OTHER_GROUP)


def is_cash(mcc):
    return str(mcc) in CASH_MCCS


def describe(mcc):
    return DESCRIPTIONS.get(str(mcc), f"MCC {mcc}")
