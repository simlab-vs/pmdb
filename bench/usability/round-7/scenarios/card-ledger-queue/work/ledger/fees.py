"""Programme fees charged by the ledger.

- FX fee: ``fx_fee_bp`` basis points of the billing amount, on clearings in a
  currency other than the programme's. Refunds don't give the fee back.
- ATM fee: a fixed fee per cash withdrawal, except at ATMs in the
  programme's home country.
"""

from .mcc import is_cash
from .money import basis_points

_config = {"currency": "EUR", "fx_fee_bp": 0, "atm_fee": 0, "free_country": ""}


def configure(settings):
    _config.update(
        currency=settings.currency,
        fx_fee_bp=settings.fx_fee_bp,
        atm_fee=settings.atm_fee,
        free_country=settings.atm_fee_free_country,
    )


def fx_fee(currency, billing_amount):
    if currency == _config["currency"]:
        return 0
    return basis_points(billing_amount, _config["fx_fee_bp"])


def atm_fee(mcc, country):
    if not is_cash(mcc):
        return 0
    if country == _config["free_country"]:
        return 0
    return _config["atm_fee"]
