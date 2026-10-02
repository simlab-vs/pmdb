"""Stock held at the sites of a warehouse network, as FIFO lots with their unit costs.

All costs are integers in cents. Quantities are integers in units of the item.
"""


def divide_half_up(numerator, denominator):
  """Returns `numerator / denominator` rounded to the nearest integer, ties away from zero."""
  if denominator == 0:
    return 0
  sign = -1 if (numerator < 0) != (denominator < 0) else 1
  numerator, denominator = abs(numerator), abs(denominator)
  quotient, remainder = divmod(numerator, denominator)
  if 2 * remainder >= denominator:
    quotient += 1
  return sign * quotient


class Lot:
  """A quantity of one item that entered a site together, at a single unit cost.

  `day` is the day the goods first entered the network; it is kept when a lot moves between
  sites so that FIFO order and ageing reflect the original receipt. `expires` is the first day
  on which the goods may no longer be sold, or None for goods that do not perish.
  """

  __slots__ = ("lot_id", "sku", "qty", "unit_cost", "day", "expires")

  def __init__(self, lot_id, sku, qty, unit_cost, day, expires=None):
    self.lot_id = lot_id
    self.sku = sku
    self.qty = qty
    self.unit_cost = unit_cost
    self.day = day
    self.expires = expires

  def value(self):
    return self.qty * self.unit_cost

  def is_expired(self, day):
    return self.expires is not None and day >= self.expires

  def sort_key(self):
    return (self.day, self.lot_id)


class Portion:
  """A quantity taken out of a lot: what was removed and what it cost."""

  __slots__ = ("qty", "unit_cost", "day", "expires")

  def __init__(self, qty, unit_cost, day, expires):
    self.qty = qty
    self.unit_cost = unit_cost
    self.day = day
    self.expires = expires

  def cost(self):
    return self.qty * self.unit_cost


def portions_cost(portions):
  """Returns the total cost of a list of portions."""
  total = 0
  for portion in portions:
    total += portion.cost()
  return total


def portions_quantity(portions):
  return sum(p.qty for p in portions)


class LotQueue:
  """The lots of one item at one site, consumed first in, first out."""

  def __init__(self, sku):
    self.sku = sku
    self.lots = []

  def add(self, lot):
    """Inserts `lot` keeping the queue ordered by receipt day, then lot id."""
    if lot.qty <= 0:
      return
    index = len(self.lots)
    while index > 0 and self.lots[index - 1].sort_key() > lot.sort_key():
      index -= 1
    self.lots.insert(index, lot)

  def quantity(self):
    return sum(lot.qty for lot in self.lots)

  def value(self):
    return sum(lot.value() for lot in self.lots)

  def take(self, qty):
    """Removes up to `qty` units, oldest first, and returns the portions taken."""
    portions = []
    remaining = qty
    while remaining > 0 and self.lots:
      lot = self.lots[0]
      used = min(lot.qty, remaining)
      portions.append(Portion(used, lot.unit_cost, lot.day, lot.expires))
      lot.qty -= used
      remaining -= used
      if lot.qty == 0:
        self.lots.pop(0)
    return portions

  def expire(self, day):
    """Removes the lots that have expired on `day` and returns them as portions."""
    expired = []
    kept = []
    for lot in self.lots:
      if lot.is_expired(day):
        expired.append(Portion(lot.qty, lot.unit_cost, lot.day, lot.expires))
      else:
        kept.append(lot)
    self.lots = kept
    return expired

  def average_cost(self):
    """Returns the quantity-weighted average unit cost, or None when the queue is empty."""
    qty = self.quantity()
    if qty == 0:
      return None
    return divide_half_up(self.value(), qty)


class SiteStock:
  """Everything stored at one site, with the quantities reserved for open orders."""

  def __init__(self, code, zone, capacity=None):
    self.code = code
    self.zone = zone
    self.capacity = capacity
    self.queues = {}
    self.reserved = {}

  def queue(self, sku):
    if sku not in self.queues:
      self.queues[sku] = LotQueue(sku)
    return self.queues[sku]

  def on_hand(self, sku):
    queue = self.queues.get(sku)
    return queue.quantity() if queue is not None else 0

  def reserved_qty(self, sku):
    return self.reserved.get(sku, 0)

  def available(self, sku):
    """Returns the units of `sku` on hand that are not reserved for an order."""
    return max(0, self.on_hand(sku) - self.reserved_qty(sku))

  def shortfall(self, sku):
    """Returns how many reserved units of `sku` are no longer physically on hand."""
    return max(0, self.reserved_qty(sku) - self.on_hand(sku))

  def reserve(self, sku, qty):
    """Reserves up to `qty` available units of `sku` and returns how many were reserved."""
    granted = min(qty, self.available(sku))
    if granted > 0:
      self.reserved[sku] = self.reserved_qty(sku) + granted
    return granted

  def release(self, sku, qty):
    """Gives back `qty` reserved units of `sku`."""
    left = self.reserved_qty(sku) - qty
    if left > 0:
      self.reserved[sku] = left
    else:
      self.reserved.pop(sku, None)

  def total_units(self):
    return sum(queue.quantity() for queue in self.queues.values())

  def free_capacity(self, incoming=0):
    """Returns how many more units fit at the site, or None when it is unbounded."""
    if self.capacity is None:
      return None
    return max(0, self.capacity - self.total_units() - incoming)

  def value(self):
    return sum(queue.value() for queue in self.queues.values())

  def lot_count(self):
    return sum(len(queue.lots) for queue in self.queues.values())

  def skus(self):
    return sorted(sku for sku, queue in self.queues.items() if queue.lots)
