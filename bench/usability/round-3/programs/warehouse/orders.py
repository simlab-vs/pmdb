"""Customer orders, their lines and the book of backordered quantities."""


class OrderLine:
  """One item of an order and how much of it is reserved, waiting, shipped or gone.

  The ordered quantity is always split between the states: reserved at the site, backordered
  until stock arrives, picked (shipped), lost when it could not be supplied, and cancelled.
  """

  def __init__(self, sku, ordered):
    self.sku = sku
    self.ordered = ordered
    self.reserved = 0
    self.backordered = 0
    self.picked = 0
    self.picked_cost = 0
    self.returned = 0
    self.returned_cost = 0
    self.lost = 0
    self.cancelled = 0

  def open_qty(self):
    """Returns the quantity still to be shipped."""
    return self.reserved + self.backordered

  def returnable(self):
    return self.picked - self.returned

  def unit_cost_of_shipped(self, qty):
    """Returns the cost of `qty` of the units still held by the customer.

    The cost is spread evenly over the shipped units that have not come back yet, so returning
    every unit credits exactly what was charged.
    """
    held = self.returnable()
    if held <= 0:
      return 0
    held_cost = self.picked_cost - self.returned_cost
    if qty >= held:
      return held_cost
    return held_cost * qty // held


class Order:
  """A customer order placed at one site."""

  def __init__(self, order_id, site, day, priority, seq):
    self.order_id = order_id
    self.site = site
    self.day = day
    self.priority = priority
    self.seq = seq
    self.lines = []
    self.cancelled = False

  def add_line(self, sku, qty):
    """Adds `qty` units of `sku`, merging with an existing line for the same item."""
    for line in self.lines:
      if line.sku == sku:
        line.ordered += qty
        return line
    line = OrderLine(sku, qty)
    self.lines.append(line)
    return line

  def line_for(self, sku):
    for line in self.lines:
      if line.sku == sku:
        return line
    return None

  def rank(self):
    """Returns the key ordering orders by urgency: lower priority number first, then age."""
    return (self.priority, self.seq)

  def status(self):
    if self.cancelled:
      return "cancelled"
    ordered = sum(line.ordered - line.lost for line in self.lines)
    picked = sum(line.picked for line in self.lines)
    if ordered > 0 and picked >= ordered:
      return "shipped"
    if picked > 0:
      return "partial"
    if any(line.backordered > 0 for line in self.lines):
      return "waiting"
    if ordered == 0:
      return "unfilled"
    return "open"


class BackorderBook:
  """The backordered order lines of the network, grouped by site and item."""

  def __init__(self):
    self.entries = {}
    self.filled_units = 0
    self.fill_events = 0
    self.created = 0

  def add(self, order, line, qty):
    """Records that `qty` units of `line` wait for stock at the order's site."""
    if qty <= 0:
      return
    key = (order.site, line.sku)
    waiting = self.entries.setdefault(key, [])
    if order not in waiting:
      waiting.append(order)
      self.created += 1
    line.backordered += qty

  def waiting(self, site, sku):
    """Returns the orders waiting for `sku` at `site`, most urgent first."""
    orders = list(self.entries.get((site, sku), []))
    orders.sort(key=lambda order: order.rank())
    return orders

  def settle(self, site, sku, order, qty):
    """Moves `qty` waiting units of the order's line for `sku` to its reservation."""
    line = order.line_for(sku)
    moved = min(qty, line.backordered)
    line.backordered -= moved
    line.reserved += moved
    self.filled_units += moved
    if moved > 0:
      self.fill_events += 1
    if line.backordered == 0:
      self.discard(site, sku, order)
    return moved

  def discard(self, site, sku, order):
    waiting = self.entries.get((site, sku))
    if waiting is None:
      return
    if order in waiting:
      waiting.remove(order)
    if not waiting:
      del self.entries[(site, sku)]

  def open_lines(self):
    return sum(len(orders) for orders in self.entries.values())

  def open_units(self):
    total = 0
    for (site, sku), orders in self.entries.items():
      for order in orders:
        total += order.line_for(sku).backordered
    return total

  def open_by_site(self):
    counts = {}
    for (site, sku), orders in self.entries.items():
      counts[site] = counts.get(site, 0) + len(orders)
    return counts
