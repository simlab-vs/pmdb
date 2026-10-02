"""Computes invoices for orders: line totals, volume discounts, coupons, taxes and currencies.

All amounts are integers in minor units (cents) of the order's currency, except exchange rates and
percentages, which are given in basis points (1 bp = 0.01%).
"""

# Tax rates in basis points, by region then by product category.
TAX_RATES = {
  "north": {"food": 500, "books": 0, "electronics": 2000, "clothing": 1200},
  "south": {"food": 700, "books": 500, "electronics": 1800, "clothing": 1500},
  "island": {"food": 0, "books": 0, "electronics": 1000, "clothing": 800},
}

# Volume discounts: (minimum quantity, discount in basis points), from the largest threshold.
VOLUME_TIERS = [(100, 1500), (50, 1000), (20, 500), (10, 200)]

# Exchange rates from the base currency (EUR) to others, in basis points.
EXCHANGE_RATES = {"EUR": 10000, "USD": 10850, "GBP": 8530, "CHF": 9420}

# Coupons, by code: (kind, amount, minimum subtotal in cents).
COUPONS = {
  "WELCOME10": ("percent", 1000, 0),
  "BIG50": ("fixed", 5000, 30000),
  "BOOKWORM": ("category", 1500, 0),
}


def divide_rounding_half_even(numerator, denominator):
  """Returns `numerator / denominator` rounded to the nearest integer, ties to even."""
  quotient, remainder = divmod(numerator, denominator)
  twice = 2 * remainder
  if twice > denominator or (twice == denominator and quotient % 2 == 1):
    quotient += 1
  return quotient


def basis_points(amount, bps):
  """Returns `bps` basis points of `amount`, rounded half to even."""
  return divide_rounding_half_even(amount * bps, 10000)


def volume_discount_rate(quantity):
  """Returns the volume discount, in basis points, granted for `quantity` units of a product."""
  for threshold, rate in VOLUME_TIERS:
    if quantity >= threshold:
      return rate
  return 0


def line_subtotal(line):
  """Returns the price of `line` after its volume discount."""
  gross = line["unit_price"] * line["quantity"]
  return gross - basis_points(gross, volume_discount_rate(line["quantity"]))


def coupon_reductions(lines, subtotals, code):
  """Returns the reduction granted by coupon `code` on each line, given their subtotals."""
  reductions = [0] * len(lines)
  if code is None or code not in COUPONS:
    return reductions

  kind, amount, minimum = COUPONS[code]
  total = sum(subtotals)
  if total < minimum:
    return reductions

  if kind == "percent":
    reductions = [basis_points(s, amount) for s in subtotals]
  elif kind == "category":
    reductions = [
      basis_points(s, amount) if l["category"] == "books" else 0 for l, s in zip(lines, subtotals)]
  elif kind == "fixed":
    reductions = spread(min(amount, total), subtotals)
  return reductions


def spread(amount, weights):
  """Splits `amount` across `weights` proportionally, giving leftover cents to the first lines."""
  total = sum(weights)
  if total == 0:
    return [0] * len(weights)
  shares = [amount * w // total for w in weights]
  leftover = amount - sum(shares)
  for i in range(len(shares)):
    if leftover == 0:
      break
    if weights[i] > 0:
      shares[i] += 1
      leftover -= 1
  return shares


def line_tax(line, net, region):
  """Returns the tax due on a line whose net price is `net`, in `region`."""
  rate = TAX_RATES[region][line["category"]]
  return basis_points(net, rate)


def convert(amount, currency):
  """Converts `amount` from EUR cents to cents of `currency`."""
  return basis_points(amount, EXCHANGE_RATES[currency])


def invoice(order):
  """Returns the invoice for `order` as a dictionary."""
  lines = order["lines"]
  region = order["region"]
  subtotals = [line_subtotal(l) for l in lines]
  reductions = coupon_reductions(lines, subtotals, order.get("coupon"))
  nets = [s - r for s, r in zip(subtotals, reductions)]
  taxes = [line_tax(l, n, region) for l, n in zip(lines, nets)]

  currency = order.get("currency", "EUR")
  rows = []
  for l, n, t in zip(lines, nets, taxes):
    rows.append({"sku": l["sku"], "net": convert(n, currency), "tax": convert(t, currency)})

  net_total = sum(r["net"] for r in rows)
  tax_total = sum(r["tax"] for r in rows)
  return {
    "currency": currency,
    "rows": rows,
    "net": net_total,
    "tax": tax_total,
    "total": net_total + tax_total,
  }


def format_cents(amount):
  """Returns `amount` cents as a decimal string."""
  sign = "-" if amount < 0 else ""
  amount = abs(amount)
  return f"{sign}{amount // 100}.{amount % 100:02d}"
