"""VAT on quotes.

The shop is registered in Germany.  Business customers in another EU
country who gave a VAT number are invoiced without VAT (reverse charge).
Customers outside the EU are quoted with their country's rate, collected
at import.
"""

from .money import percent_of

HOME_COUNTRY = "DE"
EU = {"AT", "BE", "DE", "DK", "ES", "FI", "FR", "IE", "IT", "LU", "NL", "PT", "SE"}


def reverse_charge(customer, region):
    """Whether ``customer`` in ``region`` is invoiced without VAT."""
    return (
        customer["tier"] == "trade"
        and bool(customer.get("vat_id"))
        and region.code in EU
        and region.code != HOME_COUNTRY
    )


def vat_amount(net, customer, region):
    """The VAT on ``net`` minor units for ``customer`` in ``region``."""
    if reverse_charge(customer, region):
        return 0
    return percent_of(net, region.vat_percent)
