"""Bills: charge lines, totals and VAT, in pounds rounded to pence."""

from decimal import ROUND_HALF_UP, Decimal

from . import periods, tariffs

_PENNY = Decimal("0.01")


def money(value):
    """Round to pence, halves away from zero."""
    return float(Decimal(str(value)).quantize(_PENNY, rounding=ROUND_HALF_UP))


def charge_line(description, quantity, unit_price, unit):
    return {
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "amount": money(quantity * unit_price),
    }


def charge_lines(tariff, kwh, days, fraction):
    lines = [charge_line("Standing charge", days, tariff.standing_per_day, "day")]
    bands = tariffs.energy_bands(kwh, tariffs.scaled_tiers(tariff.tiers, fraction))
    for number, (band_kwh, rate) in enumerate(bands, 1):
        label = "Energy" if len(bands) == 1 else f"Energy, band {number}"
        lines.append(charge_line(label, band_kwh, rate, "kWh"))
    if tariff.levy_per_kwh:
        lines.append(charge_line("Climate change levy", kwh, tariff.levy_per_kwh, "kWh"))
    return lines


def compose_bill(account, tariff, kwh, basis, days, period):
    """The bill of ``account`` for ``days`` of ``period``."""
    fraction = periods.fraction_of_period(period, days)
    lines = charge_lines(tariff, kwh, days, fraction)
    net = money(sum(Decimal(str(line["amount"])) for line in lines))
    vat = money(net * tariff.vat_rate)
    return {
        "account": account.account,
        "name": account.name,
        "tariff": tariff.code,
        "basis": basis,
        "days": days,
        "kwh": kwh,
        "lines": lines,
        "net": net,
        "vat": vat,
        "gross": money(net + vat),
    }
