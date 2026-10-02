"""Recalculates a workbook stored in a JSON file and prints requested cells and statistics.

The file holds `sheets`, mapping each sheet name to its cells (address to raw content, formulas
starting with '='), and `requests`, the references of the cells to print.
"""

import json
import sys

from evaluate import ErrorValue, format_number
from workbook import Workbook, cell_name


def show(value):
  """Returns how a value is displayed in a cell."""
  if value is None:
    return "(empty)"
  if isinstance(value, ErrorValue):
    return value.code
  if isinstance(value, bool):
    return "TRUE" if value else "FALSE"
  if isinstance(value, float):
    return format_number(value)
  return repr(value)


def sheet_statistics(workbook, sheet):
  """Returns the counts of numbers, text, booleans and errors on `sheet`, and its numeric total."""
  stats = {"numbers": 0, "text": 0, "booleans": 0, "errors": 0, "sum": 0.0}
  for key, cell in workbook.cells.items():
    if key[0] != sheet:
      continue
    value = cell.value
    if isinstance(value, ErrorValue):
      stats["errors"] += 1
    elif isinstance(value, bool):
      stats["booleans"] += 1
    elif isinstance(value, float):
      stats["numbers"] += 1
      stats["sum"] += value
    elif isinstance(value, str):
      stats["text"] += 1
  return stats


def error_counts(workbook):
  counts = {}
  for cell in workbook.cells.values():
    if isinstance(cell.value, ErrorValue):
      counts[cell.value.code] = counts.get(cell.value.code, 0) + 1
  return counts


def extremes(workbook):
  """Returns the formula cells with the smallest and the largest numeric values."""
  low = high = None
  for key in sorted(workbook.cells, key=workbook.sort_key):
    cell = workbook.cells[key]
    if not cell.is_formula() or isinstance(cell.value, bool) or not isinstance(cell.value, float):
      continue
    if low is None or cell.value < low.value:
      low = cell
    if high is None or cell.value > high.value:
      high = cell
  return low, high


def checksum(workbook):
  """Returns a position-weighted sum of the numeric values of all formulas."""
  total = 0.0
  for position, key in enumerate(sorted(workbook.cells, key=workbook.sort_key), start=1):
    value = workbook.cells[key].value
    if workbook.cells[key].is_formula() and isinstance(value, float) and not isinstance(value, bool):
      total += position * value
  return total


def main(path):
  with open(path) as f:
    data = json.load(f)
  workbook = Workbook(data["sheets"])
  evaluated = workbook.recalculate()
  invalid = sum(1 for cell in workbook.cells.values() if cell.kind == "invalid")
  print(f"cells {len(workbook.cells)}, formulas evaluated {evaluated}, "
        f"in cycles {len(workbook.cycle_cells)}, invalid {invalid}")

  for reference in data["requests"]:
    value, exists = workbook.value_of(reference)
    print(f"  {reference} = {show(value) if exists else '#REF!'}")

  for sheet in workbook.order:
    stats = sheet_statistics(workbook, sheet)
    print(f"sheet {sheet}: {stats['numbers']} numbers (sum {stats['sum']:.12g}), "
          f"{stats['text']} text, {stats['booleans']} booleans, {stats['errors']} errors")

  errors = error_counts(workbook)
  print("errors: " + (", ".join(f"{code} {errors[code]}" for code in sorted(errors)) or "none"))
  deepest = workbook.deepest()
  if deepest is not None:
    print(f"deepest: {cell_name(deepest.key)} at level {deepest.level}")
  low, high = extremes(workbook)
  if low is not None:
    print(f"min: {cell_name(low.key)} = {show(low.value)}; max: {cell_name(high.key)} = {show(high.value)}")
  print(f"checksum {checksum(workbook):.12g}")


if __name__ == "__main__":
  main(sys.argv[1])
