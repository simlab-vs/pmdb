"""VAT treatment of invoices."""


def tax_treatment(customer, settings):
    """Return ``(rate, label)`` for a customer.

    Domestic customers pay the seller's VAT. Business customers elsewhere in the
    EU with a VAT ID are invoiced under the reverse-charge mechanism; consumers
    in the EU pay their own country's rate. Customers outside the EU pay no VAT.
    """
    country = customer["country"]
    if country == settings.seller_country:
        return settings.vat_rates[country], "VAT"
    if country in settings.eu_countries:
        if customer["vat_id"]:
            return 0.0, "Reverse charge"
        return settings.vat_rates.get(country, settings.vat_rates[settings.seller_country]), "VAT"
    return 0.0, "Outside the scope of EU VAT"
