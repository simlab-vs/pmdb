"""A workbook of named sheets: cell contents, the dependency graph and recalculation.

Recalculation finds the cells that take part in reference cycles, which all evaluate to #CYCLE!,
then evaluates the remaining formulas in topological order so that every formula sees the final
values of the cells it reads.
"""

import heapq

from evaluate import CYCLE, SYNTAX, Evaluator, FormulaError, parse_number
from formula import FormulaSyntaxError, format_address, parse_formula, references, split_address


class Cell:
  """The content of one cell and, once computed, its value."""

  __slots__ = ("key", "raw", "kind", "node", "value", "depends", "level")

  def __init__(self, key, raw):
    self.key = key
    self.raw = raw
    self.kind = None
    self.node = None
    self.value = None
    self.depends = []
    self.level = 0

  def is_formula(self):
    return self.kind == "formula"


def interpret(cell):
  """Sets the kind of `cell` and its constant value or formula tree from its raw text."""
  raw = cell.raw
  if raw.startswith("="):
    cell.kind = "formula"
    try:
      cell.node = parse_formula(raw[1:])
    except FormulaSyntaxError:
      cell.kind = "invalid"
      cell.value = SYNTAX
    return
  if raw.startswith("'"):
    cell.kind = "text"
    cell.value = raw[1:]
    return
  if raw.upper() in ("TRUE", "FALSE"):
    cell.kind = "boolean"
    cell.value = raw.upper() == "TRUE"
    return
  number = parse_number(raw)
  if number is not None:
    cell.kind = "number"
    cell.value = number
  else:
    cell.kind = "text"
    cell.value = raw


class Workbook:
  """Sheets of cells keyed by (sheet, column, row)."""

  def __init__(self, sheets):
    self.order = list(sheets)
    self.cells = {}
    for sheet_index, name in enumerate(self.order):
      for address, raw in sheets[name].items():
        position = split_address(address)
        if position is None:
          continue
        key = (name, position[0], position[1])
        cell = Cell(key, str(raw))
        interpret(cell)
        self.cells[key] = cell
    self.cycle_cells = set()

  def sort_key(self, key):
    """Orders cells by sheet (in file order), then row, then column."""
    sheet, column, row = key
    return (self.order.index(sheet), row, column)

  def lookup(self, sheet, column, row):
    if sheet not in self.order:
      raise KeyError(sheet)
    cell = self.cells.get((sheet, column, row))
    return None if cell is None else cell.value

  def formulas(self):
    return [cell for cell in self.cells.values() if cell.is_formula()]

  def link(self):
    """Records for every formula the existing cells it reads."""
    for cell in self.formulas():
      seen = set()
      depends = []
      for key in references(cell.node, cell.key[0]):
        if key in self.cells and key not in seen:
          seen.add(key)
          depends.append(key)
      cell.depends = depends

  def find_cycles(self):
    """Returns the cells on reference cycles, using Tarjan's strongly connected components."""
    index = {}
    low = {}
    on_stack = set()
    stack = []
    in_cycle = set()
    counter = 0
    for start in sorted(self.cells, key=self.sort_key):
      if start in index:
        continue
      work = [(start, 0)]
      while work:
        key, child = work.pop()
        if child == 0:
          index[key] = low[key] = counter
          counter += 1
          stack.append(key)
          on_stack.add(key)
        depends = self.cells[key].depends
        if child < len(depends):
          work.append((key, child + 1))
          target = depends[child]
          if target not in index:
            work.append((target, 0))
          elif target in on_stack:
            low[key] = min(low[key], index[target])
          continue
        if low[key] == index[key]:
          component = []
          while True:
            member = stack.pop()
            on_stack.discard(member)
            component.append(member)
            if member == key:
              break
          if len(component) > 1 or key in self.cells[key].depends:
            in_cycle.update(component)
        if work:
          parent = work[-1][0]
          low[parent] = min(low[parent], low[key])
    return in_cycle

  def evaluation_order(self, excluded):
    """Returns the formulas outside `excluded` in an order where dependencies come first.

    Among the cells that are ready at the same time, the first in sheet, row, column order goes
    first. Each cell also receives its level: one more than the deepest formula it reads.
    """
    pending = {}
    readers = {}
    for cell in self.formulas():
      if cell.key in excluded:
        continue
      count = 0
      for dep in cell.depends:
        if dep in excluded or not self.cells[dep].is_formula():
          continue
        count += 1
        readers.setdefault(dep, []).append(cell.key)
      pending[cell.key] = count
    ready = [(self.sort_key(key), key) for key, count in pending.items() if count == 0]
    heapq.heapify(ready)
    order = []
    while ready:
      _, key = heapq.heappop(ready)
      cell = self.cells[key]
      cell.level = 1 + max((self.cells[d].level for d in cell.depends), default=0)
      order.append(cell)
      for reader in readers.get(key, []):
        pending[reader] -= 1
        if pending[reader] == 0:
          heapq.heappush(ready, (self.sort_key(reader), reader))
    return order

  def recalculate(self):
    """Computes the value of every formula; returns the number of formulas evaluated."""
    self.link()
    self.cycle_cells = self.find_cycles()
    for key in self.cycle_cells:
      self.cells[key].value = CYCLE
    order = self.evaluation_order(self.cycle_cells)
    for cell in order:
      cell.value = self.evaluate_cell(cell)
    return len(order)

  def evaluate_cell(self, cell):
    evaluator = Evaluator(self.lookup, cell.key[0])
    try:
      return evaluator.value(cell.node)
    except FormulaError as error:
      return error.error

  def value_of(self, reference):
    """Returns the value of the cell named `reference` (like `Sheet!B4`) and whether it exists."""
    sheet, _, address = reference.rpartition("!")
    sheet = sheet or self.order[0]
    position = split_address(address)
    if position is None or sheet not in self.order:
      return None, False
    return self.lookup(sheet, position[0], position[1]), True

  def deepest(self):
    """Returns the formula cell with the highest level, the first in sheet order on ties."""
    best = None
    for cell in sorted(self.formulas(), key=lambda c: self.sort_key(c.key)):
      if cell.key in self.cycle_cells:
        continue
      if best is None or cell.level > best.level:
        best = cell
    return best


def cell_name(key):
  sheet, column, row = key
  return f"{sheet}!{format_address(column, row)}"
