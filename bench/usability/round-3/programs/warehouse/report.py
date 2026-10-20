"""Summaries of the state of a warehouse network at the end of a period."""

from stock import divide_half_up

# Number of items listed in each ranking.
TOP_ITEMS = 5

# Modulus of the reconciliation checksum.
CHECKSUM_MODULUS = 1_000_003


def format_cents(amount):
  """Returns `amount` cents as a decimal string."""
  sign = "-" if amount < 0 else ""
  amount = abs(amount)
  return f"{sign}{amount // 100}.{amount % 100:02d}"


def site_summary(site):
  """Returns the units, value, lot count and reserved units held at `site`."""
  reserved = sum(site.reserved.values())
  return {
    "code": site.code,
    "units": site.total_units(),
    "value": site.value(),
    "lots": site.lot_count(),
    "reserved": reserved,
  }


def transit_summary(warehouse):
  units = sum(t.quantity() for t in warehouse.in_transit)
  value = sum(t.value() for t in warehouse.in_transit)
  return units, value


def below_reorder_point(warehouse):
  """Returns the number of (site, item) pairs whose free stock is below the item's reorder point."""
  count = 0
  for code in sorted(warehouse.sites):
    site = warehouse.sites[code]
    for sku, item in sorted(warehouse.items.items()):
      point = item.get("reorder_point", 0)
      if point > 0 and site.available(sku) < point:
        count += 1
  return count


def order_statuses(warehouse):
  counts = {}
  for order in warehouse.orders.values():
    status = order.status()
    counts[status] = counts.get(status, 0) + 1
  return counts


def fill_rate(warehouse):
  """Returns the permille of ordered units, not cancelled, that were shipped."""
  wanted = 0
  shipped = 0
  for order in warehouse.orders.values():
    for line in order.lines:
      wanted += line.ordered - line.cancelled
      shipped += line.picked
  if wanted <= 0:
    return 0
  return divide_half_up(shipped * 1000, wanted)


def ranking(stats, key, limit=TOP_ITEMS):
  """Returns the items with the largest positive `key`, ties broken by SKU."""
  rows = [s for s in stats.values() if key(s) > 0]
  rows.sort(key=lambda s: (-key(s), s.sku))
  return rows[:limit]


def value_by_item(warehouse):
  values = {}
  for site in warehouse.sites.values():
    for sku, queue in site.queues.items():
      values[sku] = values.get(sku, 0) + queue.value()
  return values


def average_age(stats):
  """Returns the average age of shipped goods in tenths of days."""
  units = sum(s.age_units for s in stats.values())
  days = sum(s.age_days for s in stats.values())
  if units == 0:
    return 0
  return divide_half_up(days * 10, units)


def grand_total(warehouse):
  """Returns the value that entered the network, reconstructed from where it ended up.

  Everything received is either still in stock, in transit, sold, scrapped, lost to shrinkage or
  expiry; gains, freight and return credits are the value created inside the network.
  """
  ledger = warehouse.ledger
  stock = sum(site.value() for site in warehouse.sites.values())
  _, transit = transit_summary(warehouse)
  outflow = ledger.cogs + ledger.scrap + ledger.shrinkage + ledger.expired
  inside = ledger.gains + ledger.freight
  return stock + transit + outflow - inside


def checksum(warehouse):
  """Returns a checksum of the remaining lots: their quantities and costs, weighted by position."""
  total = 0
  position = 1
  for code in sorted(warehouse.sites):
    site = warehouse.sites[code]
    for sku in site.skus():
      for lot in site.queue(sku).lots:
        total = (total + position * (lot.qty * 31 + lot.unit_cost)) % CHECKSUM_MODULUS
        position += 1
  return total


def render(warehouse):
  """Returns the lines of the end-of-period report."""
  lines = [f"day {warehouse.day}"]
  for code in sorted(warehouse.sites):
    s = site_summary(warehouse.sites[code])
    lines.append(f"site {s['code']}: {s['units']} units in {s['lots']} lots, "
                 f"{s['reserved']} reserved, value {format_cents(s['value'])}")
  units, value = transit_summary(warehouse)
  lines.append(f"in transit: {units} units, value {format_cents(value)}")

  ledger = warehouse.ledger
  lines.append(f"cogs {format_cents(ledger.cogs)} (returns credited {format_cents(ledger.returns_credit)})")
  lines.append(f"scrap {format_cents(ledger.scrap)}, shrinkage {format_cents(ledger.shrinkage)}, "
               f"expired {format_cents(ledger.expired)}")
  lines.append(f"gains {format_cents(ledger.gains)}, freight {format_cents(ledger.freight)}, "
               f"refused {format_cents(ledger.refused)}")

  statuses = order_statuses(warehouse)
  lines.append("orders: " + ", ".join(f"{k} {statuses[k]}" for k in sorted(statuses)))
  book = warehouse.backorders
  by_site = book.open_by_site()
  lines.append(f"backorders: {book.open_lines()} open lines, {book.open_units()} units "
               f"({', '.join(f'{k} {by_site[k]}' for k in sorted(by_site)) or 'none'}); "
               f"{book.created} created, {book.fill_events} fills, {book.filled_units} units filled")
  lost = sum(s.units_lost for s in warehouse.stats.values())
  rate = fill_rate(warehouse)
  lines.append(f"fill rate {rate // 10}.{rate % 10}%, lost units {lost}, "
               f"below reorder point {below_reorder_point(warehouse)}")

  lines.append("top items by cogs:")
  for s in ranking(warehouse.stats, lambda s: s.cogs):
    lines.append(f"  {s.sku:<8} {s.units_sold:>5} sold {s.units_returned:>4} returned  "
                 f"{format_cents(s.cogs):>12}")
  values = value_by_item(warehouse)
  top = sorted((v, sku) for sku, v in values.items() if v > 0)
  top.sort(key=lambda pair: (-pair[0], pair[1]))
  lines.append("top items by stock value: " + ", ".join(
    f"{sku} {format_cents(v)}" for v, sku in top[:TOP_ITEMS]))

  age = average_age(warehouse.stats)
  lines.append(f"average age at pick: {age // 10}.{age % 10} days")
  c = warehouse.counts
  lines.append(f"events: {c['receipts']} receipts, {c['picks']} picks, {c['returns']} returns, "
               f"{c['transfers']} transfers, {c['adjustments']} adjustments")
  lines.append(f"counts: {c['counts']} ({c['discrepancies']} off), expiries {c['expiries']}, "
               f"reallocations {c['reallocations']}, preemptions {c['preemptions']}")
  lines.append(f"grand total {format_cents(grand_total(warehouse))}, checksum {checksum(warehouse)}")
  return lines
