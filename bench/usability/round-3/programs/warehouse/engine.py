"""Applies the events of a period to a network of warehouse sites.

The engine keeps the stock of every site as FIFO lots, reserves stock for orders, backorders what
cannot be reserved, ships picked goods at their FIFO cost, and keeps the ledger of every movement
of value: cost of goods sold, scrapped returns, inventory shrinkage and gains, expired goods and
transfer freight.
"""

from orders import BackorderBook, Order
from stock import Lot, SiteStock, divide_half_up, portions_cost, portions_quantity

# Freight for moving one unit between sites, in cents: a fixed handling charge plus a charge per
# zone crossed, scaled by the weight class of the item (in tenths).
FREIGHT_HANDLING = 15
FREIGHT_PER_ZONE = 40
WEIGHT_FACTORS = {"light": 10, "medium": 16, "heavy": 35}

# Orders with this priority are rush orders: they may take stock reserved for other orders.
RUSH_PRIORITY = 0

# Days goods spend between sites, by number of zones crossed (more zones take the last value).
TRANSIT_DAYS = [0, 1, 2, 2, 3]


class Ledger:
  """Totals of the value that left or entered the stock, in cents."""

  def __init__(self):
    self.cogs = 0
    self.returns_credit = 0
    self.scrap = 0
    self.shrinkage = 0
    self.gains = 0
    self.expired = 0
    self.freight = 0
    self.refused = 0


class ItemStats:
  """What happened to one item over the period."""

  def __init__(self, sku):
    self.sku = sku
    self.units_sold = 0
    self.cogs = 0
    self.units_returned = 0
    self.units_lost = 0
    self.age_units = 0
    self.age_days = 0

  def record_pick(self, portions, day):
    """Adds the shipped portions, with the age of their goods on `day`."""
    for portion in portions:
      self.units_sold += portion.qty
      self.cogs += portion.cost()
      self.age_units += portion.qty
      self.age_days += portion.qty * (day - portion.day)


class InTransit:
  """Goods travelling from one site to another."""

  def __init__(self, source, target, sku, portions, arrival, freight_per_unit):
    self.source = source
    self.target = target
    self.sku = sku
    self.portions = portions
    self.arrival = arrival
    self.freight_per_unit = freight_per_unit

  def quantity(self):
    return portions_quantity(self.portions)

  def value(self):
    return portions_cost(self.portions) + self.quantity() * self.freight_per_unit


def freight_per_unit(source, target, weight):
  """Returns the freight charged per unit moved from site `source` to site `target`."""
  zones = abs(source.zone - target.zone)
  factor = WEIGHT_FACTORS.get(weight, WEIGHT_FACTORS["medium"])
  return divide_half_up((FREIGHT_HANDLING + FREIGHT_PER_ZONE * zones) * factor, 10)


def transit_days(source, target):
  zones = abs(source.zone - target.zone)
  return TRANSIT_DAYS[min(zones, len(TRANSIT_DAYS) - 1)]


class Warehouse:
  """The state of the network of sites, updated event by event."""

  def __init__(self, sites, items):
    self.sites = {}
    for site in sites:
      self.sites[site["code"]] = SiteStock(site["code"], site.get("zone", 0), site.get("capacity"))
    self.items = {item["sku"]: dict(item) for item in items}
    self.orders = {}
    self.backorders = BackorderBook()
    self.ledger = Ledger()
    self.stats = {sku: ItemStats(sku) for sku in self.items}
    self.in_transit = []
    self.day = 0
    self.next_lot = 1
    self.next_seq = 1
    self.counts = {"receipts": 0, "picks": 0, "returns": 0, "transfers": 0, "adjustments": 0,
                   "counts": 0, "discrepancies": 0, "expiries": 0, "reallocations": 0,
                   "preemptions": 0}

  # -- Time --------------------------------------------------------------------------------------

  def advance_to(self, day):
    """Moves the clock to `day`, delivering transfers and expiring lots on each day passed."""
    while self.day < day:
      self.day += 1
      self.deliver_arrivals(self.day)
      self.expire_lots(self.day)

  def deliver_arrivals(self, day):
    arriving = [t for t in self.in_transit if t.arrival <= day]
    self.in_transit = [t for t in self.in_transit if t.arrival > day]
    for transfer in arriving:
      target = self.sites[transfer.target]
      queue = target.queue(transfer.sku)
      for portion in transfer.portions:
        unit_cost = portion.unit_cost + transfer.freight_per_unit
        queue.add(self.new_lot(transfer.sku, portion.qty, unit_cost, portion.day, portion.expires))
      self.fill_backorders(target, transfer.sku)

  def expire_lots(self, day):
    for code in sorted(self.sites):
      site = self.sites[code]
      for sku in site.skus():
        expired = site.queue(sku).expire(day)
        if not expired:
          continue
        self.counts["expiries"] += 1
        self.ledger.expired += portions_cost(expired)
        self.reallocate(site, sku)

  # -- Helpers -----------------------------------------------------------------------------------

  def new_lot(self, sku, qty, unit_cost, day, expires=None):
    lot = Lot(self.next_lot, sku, qty, unit_cost, day, expires)
    self.next_lot += 1
    return lot

  def expiry_for(self, sku, day):
    shelf_life = self.items[sku].get("shelf_life")
    return day + shelf_life if shelf_life else None

  def incoming(self, code):
    """Returns the units already on their way to site `code`."""
    return sum(t.quantity() for t in self.in_transit if t.target == code)

  def fill_backorders(self, site, sku):
    """Reserves newly available stock of `sku` for the orders waiting for it, most urgent first."""
    for order in self.backorders.waiting(site.code, sku):
      available = site.available(sku)
      if available <= 0:
        break
      line = order.line_for(sku)
      granted = site.reserve(sku, min(available, line.backordered))
      self.backorders.settle(site.code, sku, order, granted)

  def reallocate(self, site, sku):
    """Takes back reservations of `sku` that the stock left at `site` can no longer cover.

    The least urgent orders give up their reservations first. What they lose goes back to the
    backorder book, or is lost when the item cannot be backordered.
    """
    missing = site.shortfall(sku)
    if missing == 0:
      return
    self.counts["reallocations"] += 1
    holders = [o for o in self.orders.values()
               if o.site == site.code and not o.cancelled and o.line_for(sku) is not None]
    holders.sort(key=lambda order: order.rank(), reverse=True)
    for order in holders:
      if missing <= 0:
        break
      line = order.line_for(sku)
      taken = min(line.reserved, missing)
      if taken == 0:
        continue
      line.reserved -= taken
      site.release(sku, taken)
      missing -= taken
      self.defer(order, line, taken)

  def preempt(self, site, order, line, qty):
    """Moves up to `qty` units of the line's item reserved for less urgent orders to `line`.

    Only orders that are not rush orders themselves give up stock, least urgent first; what they
    give up is deferred. Returns the number of units moved.
    """
    holders = [o for o in self.orders.values()
               if o.site == site.code and o is not order and not o.cancelled
               and o.priority > RUSH_PRIORITY and o.line_for(line.sku) is not None]
    holders.sort(key=lambda other: other.rank(), reverse=True)
    moved = 0
    for other in holders:
      if moved >= qty:
        break
      other_line = other.line_for(line.sku)
      taken = min(other_line.reserved, qty - moved)
      if taken <= 0:
        continue
      other_line.reserved -= taken
      line.reserved += taken
      moved += taken
      self.defer(other, other_line, taken)
    if moved:
      self.counts["preemptions"] += 1
    return moved

  def defer(self, order, line, qty):
    """Backorders `qty` units of `line`, or records them as lost sales."""
    if self.items[line.sku].get("backorder", True):
      self.backorders.add(order, line, qty)
    else:
      line.lost += qty
      self.stats[line.sku].units_lost += qty

  # -- Events ------------------------------------------------------------------------------------

  def apply(self, event):
    """Applies one event, after moving the clock to its day."""
    self.advance_to(event["day"])
    handler = getattr(self, "on_" + event["type"])
    handler(event)

  def on_receipt(self, event):
    site = self.sites[event["site"]]
    sku = event["sku"]
    qty = event["qty"]
    free = site.free_capacity(self.incoming(site.code))
    if free is not None and qty > free:
      self.ledger.refused += (qty - free) * event["unit_cost"]
      qty = free
    if qty <= 0:
      return
    self.counts["receipts"] += 1
    lot = self.new_lot(sku, qty, event["unit_cost"], self.day, self.expiry_for(sku, self.day))
    site.queue(sku).add(lot)
    self.fill_backorders(site, sku)

  def on_order(self, event):
    site = self.sites[event["site"]]
    order = Order(event["order"], site.code, self.day, event.get("priority", 5), self.next_seq)
    self.next_seq += 1
    self.orders[order.order_id] = order
    for entry in event["lines"]:
      line = order.add_line(entry["sku"], entry["qty"])
      wanted = entry["qty"]
      granted = site.reserve(line.sku, wanted)
      line.reserved += granted
      if granted < wanted and order.priority <= RUSH_PRIORITY:
        granted += self.preempt(site, order, line, wanted - granted)
      if granted < wanted:
        self.defer(order, line, wanted - granted)

  def on_pick(self, event):
    order = self.orders.get(event["order"])
    if order is None or order.cancelled:
      return
    site = self.sites[order.site]
    limit = event.get("limit")
    for line in order.lines:
      qty = line.reserved if limit is None else min(line.reserved, limit)
      if qty <= 0:
        continue
      portions = site.queue(line.sku).take(qty)
      taken = portions_quantity(portions)
      site.release(line.sku, taken)
      line.reserved -= taken
      line.picked += taken
      cost = portions_cost(portions)
      line.picked_cost += cost
      self.ledger.cogs += cost
      self.stats[line.sku].record_pick(portions, self.day)
      self.counts["picks"] += 1

  def on_cancel(self, event):
    order = self.orders.get(event["order"])
    if order is None or order.cancelled:
      return
    site = self.sites[order.site]
    order.cancelled = True
    for line in order.lines:
      if line.reserved > 0:
        site.release(line.sku, line.reserved)
      line.cancelled += line.open_qty()
      line.reserved = 0
      line.backordered = 0
      self.backorders.discard(site.code, line.sku, order)
      self.fill_backorders(site, line.sku)

  def on_return(self, event):
    order = self.orders.get(event["order"])
    if order is None:
      return
    line = order.line_for(event["sku"])
    if line is None:
      return
    qty = min(event["qty"], line.returnable())
    if qty <= 0:
      return
    cost = line.unit_cost_of_shipped(qty)
    line.returned += qty
    line.returned_cost += cost
    self.counts["returns"] += 1
    self.ledger.cogs -= cost
    self.ledger.returns_credit += cost
    self.stats[line.sku].units_returned += qty
    site = self.sites[order.site]
    free = site.free_capacity(self.incoming(site.code))
    if event.get("condition", "good") != "good" or (free is not None and free < qty):
      self.ledger.scrap += cost
      return
    unit_cost = divide_half_up(cost, qty)
    self.ledger.gains += unit_cost * qty - cost
    lot = self.new_lot(line.sku, qty, unit_cost, self.day, self.expiry_for(line.sku, self.day))
    site.queue(line.sku).add(lot)
    self.fill_backorders(site, line.sku)

  def on_transfer(self, event):
    source = self.sites[event["from"]]
    target = self.sites[event["to"]]
    sku = event["sku"]
    if source is target:
      return
    qty = min(event["qty"], source.available(sku))
    free = target.free_capacity(self.incoming(target.code))
    if free is not None:
      qty = min(qty, free)
    if qty <= 0:
      return
    self.counts["transfers"] += 1
    portions = source.queue(sku).take(qty)
    per_unit = freight_per_unit(source, target, self.items[sku].get("weight", "medium"))
    self.ledger.freight += per_unit * portions_quantity(portions)
    arrival = self.day + transit_days(source, target)
    self.in_transit.append(InTransit(source.code, target.code, sku, portions, arrival, per_unit))
    if arrival <= self.day:
      self.deliver_arrivals(self.day)

  def on_adjust(self, event):
    site = self.sites[event["site"]]
    self.adjust(site, event["sku"], event["delta"])

  def on_count(self, event):
    site = self.sites[event["site"]]
    sku = event["sku"]
    self.counts["counts"] += 1
    delta = event["counted"] - site.on_hand(sku)
    if delta != 0:
      self.counts["discrepancies"] += 1
      self.adjust(site, sku, delta)

  def adjust(self, site, sku, delta):
    """Corrects the stock of `sku` at `site` by `delta` units found or missing."""
    self.counts["adjustments"] += 1
    queue = site.queue(sku)
    if delta < 0:
      portions = queue.take(-delta)
      self.ledger.shrinkage += portions_cost(portions)
      self.reallocate(site, sku)
      return
    unit_cost = queue.average_cost()
    if unit_cost is None:
      unit_cost = self.items[sku].get("std_cost", 0)
    queue.add(self.new_lot(sku, delta, unit_cost, self.day, self.expiry_for(sku, self.day)))
    self.ledger.gains += delta * unit_cost
    self.fill_backorders(site, sku)


def run_events(warehouse, events):
  """Applies `events` in day order (keeping the file order within a day) and closes the period."""
  ordered = sorted(enumerate(events), key=lambda pair: (pair[1]["day"], pair[0]))
  last_day = 0
  for _, event in ordered:
    warehouse.apply(event)
    last_day = max(last_day, event["day"])
  warehouse.advance_to(last_day + 1)
  return warehouse
