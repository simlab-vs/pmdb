"""Monthly wage tax (simplified tariff).

The month's taxable pay (contribution-liable pay minus the employee's
contributions) is annualized, the tax class's basic allowance is deducted,
and the rest is taxed in bands.  The monthly tax is a twelfth of the
annual tax, rounded down to the cent.
"""


def annual_tax(taxable_annual, tax_class, rules):
    remaining = max(0, taxable_annual - rules.tax_allowance[tax_class])
    tax = 0
    for width, basis_points in rules.tax_bands:
        portion = remaining if width == 0 else min(remaining, width)
        tax += portion * basis_points
        remaining -= portion
        if remaining <= 0:
            break
    return tax // 10_000


def wage_tax(taxable_month, tax_class, rules):
    if taxable_month <= 0:
        return 0
    return annual_tax(taxable_month * 12, tax_class, rules) // 12
