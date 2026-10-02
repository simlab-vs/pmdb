"""Evaluation of formula trees: values, error propagation and the built-in functions.

Cell values are floats, strings, booleans, None for an empty cell, or an `ErrorValue`. An error met
while evaluating a formula is raised as `FormulaError` and becomes the value of the cell, so that
it propagates to every formula reading that cell, unless a function such as IFERROR catches it.
"""

import math

from formula import (MAX_COLUMN, MAX_ROW, Binary, Boolean, Call, Number, Percent, Range, Ref,
                     Text, Unary)


class ErrorValue:
  """A spreadsheet error such as #DIV/0!, identified by its code."""

  __slots__ = ("code",)

  def __init__(self, code):
    self.code = code


DIV_ZERO = ErrorValue("#DIV/0!")
VALUE = ErrorValue("#VALUE!")
REF = ErrorValue("#REF!")
NAME = ErrorValue("#NAME?")
NUM = ErrorValue("#NUM!")
CYCLE = ErrorValue("#CYCLE!")
SYNTAX = ErrorValue("#ERROR!")


class FormulaError(Exception):
  def __init__(self, error):
    super().__init__(error.code)
    self.error = error


def fail(error):
  raise FormulaError(error)


def checked(value):
  """Returns `value`, raising the error it holds if it is one."""
  if isinstance(value, ErrorValue):
    fail(value)
  return value


def finite(x):
  if math.isnan(x) or math.isinf(x):
    fail(NUM)
  return x


def parse_number(text):
  """Returns the number written in `text`, or None when it is not a number."""
  text = text.strip()
  if not text:
    return None
  try:
    value = float(text)
  except ValueError:
    return None
  if math.isnan(value) or math.isinf(value):
    return None
  return value


def to_number(value):
  """Converts an operand of arithmetic to a number."""
  checked(value)
  if value is None:
    return 0.0
  if isinstance(value, bool):
    return 1.0 if value else 0.0
  if isinstance(value, float):
    return value
  number = parse_number(value)
  if number is None:
    fail(VALUE)
  return number


def to_bool(value):
  checked(value)
  if value is None:
    return False
  if isinstance(value, bool):
    return value
  if isinstance(value, float):
    return value != 0
  upper = value.upper()
  if upper in ("TRUE", "FALSE"):
    return upper == "TRUE"
  fail(VALUE)


def format_number(x):
  """Returns the shortest usual spelling of the number `x`."""
  if x == int(x) and abs(x) < 1e15:
    return str(int(x))
  return f"{x:.10g}"


def to_text(value):
  checked(value)
  if value is None:
    return ""
  if isinstance(value, bool):
    return "TRUE" if value else "FALSE"
  if isinstance(value, float):
    return format_number(value)
  return value


def type_rank(value):
  """Orders values of different types the way comparisons do: numbers < text < booleans."""
  if isinstance(value, bool):
    return 2
  if isinstance(value, str):
    return 1
  return 0


def compare(op, left, right):
  """Applies the comparison operator `op` to two values."""
  checked(left)
  checked(right)
  if left is None:
    left = "" if isinstance(right, str) else 0.0
  if right is None:
    right = "" if isinstance(left, str) else 0.0
  if isinstance(left, str) and isinstance(right, str):
    left, right = left.lower(), right.lower()
  elif type_rank(left) != type_rank(right):
    left, right = type_rank(left), type_rank(right)
  if op == "=":
    return left == right
  if op == "<>":
    return left != right
  if op == "<":
    return left < right
  if op == ">":
    return left > right
  if op == "<=":
    return left <= right
  return left >= right


def arithmetic(op, a, b):
  if op == "+":
    return a + b
  if op == "-":
    return a - b
  if op == "*":
    return a * b
  if op == "/":
    if b == 0:
      fail(DIV_ZERO)
    return a / b
  if a == 0 and b < 0:
    fail(DIV_ZERO)
  if a < 0 and b != int(b):
    fail(NUM)
  try:
    return a ** b
  except OverflowError:
    fail(NUM)


class Evaluator:
  """Evaluates the formulas of the cells of one sheet, reading other cells through `lookup`.

  `lookup(sheet, column, row)` returns the current value of a cell, or raises KeyError when the
  sheet does not exist.
  """

  def __init__(self, lookup, sheet):
    self.lookup = lookup
    self.sheet = sheet

  def read(self, sheet, column, row):
    if column < 1 or column > MAX_COLUMN or row < 1 or row > MAX_ROW:
      fail(REF)
    try:
      return self.lookup(sheet or self.sheet, column, row)
    except KeyError:
      fail(REF)

  def range_values(self, node):
    """Returns the values of the cells of a range, row by row, including empty ones."""
    if node.left > MAX_COLUMN or node.top > MAX_ROW:
      fail(REF)
    return [self.read(node.sheet, column, row) for column, row in node.cells()]

  def value(self, node):
    """Returns the value of a node that must evaluate to a single value."""
    if isinstance(node, Number):
      return node.value
    if isinstance(node, (Text, Boolean)):
      return node.value
    if isinstance(node, Ref):
      return checked(self.read(node.sheet, node.column, node.row))
    if isinstance(node, Range):
      fail(VALUE)
    if isinstance(node, Unary):
      x = to_number(self.value(node.operand))
      return -x if node.op == "-" else x
    if isinstance(node, Percent):
      return to_number(self.value(node.operand)) / 100
    if isinstance(node, Binary):
      return self.binary(node)
    if isinstance(node, Call):
      function = FUNCTIONS.get(node.name)
      if function is None:
        fail(NAME)
      return function(self, node.args)
    fail(VALUE)

  def binary(self, node):
    left = self.value(node.left)
    right = self.value(node.right)
    if node.op == "&":
      return to_text(left) + to_text(right)
    if node.op in ("=", "<>", "<", ">", "<=", ">="):
      return compare(node.op, left, right)
    return finite(arithmetic(node.op, to_number(left), to_number(right)))

  def numbers(self, args):
    """Returns the numbers among the arguments of an aggregate such as SUM.

    Inside ranges only numeric cells count; text, booleans and empty cells are skipped. Values
    given directly as arguments are converted to numbers.
    """
    found = []
    for arg in args:
      if isinstance(arg, Range):
        for value in self.range_values(arg):
          checked(value)
          if isinstance(value, float):
            found.append(value)
      elif isinstance(arg, Ref):
        value = self.value(arg)
        if isinstance(value, float) or isinstance(value, bool):
          found.append(to_number(value))
      else:
        found.append(to_number(self.value(arg)))
    return found


def arity(args, low, high):
  if len(args) < low or len(args) > high:
    fail(VALUE)


def total(values):
  """Returns the exact sum of `values`, or fails with #NUM! when it is out of range."""
  try:
    return finite(math.fsum(values))
  except OverflowError:
    fail(NUM)


def fn_sum(ev, args):
  return total(ev.numbers(args))


def fn_average(ev, args):
  values = ev.numbers(args)
  if not values:
    fail(DIV_ZERO)
  return total(values) / len(values)


def fn_min(ev, args):
  values = ev.numbers(args)
  return min(values) if values else 0.0


def fn_max(ev, args):
  values = ev.numbers(args)
  return max(values) if values else 0.0


def fn_count(ev, args):
  return float(len(ev.numbers(args)))


def round_half_away(x, digits):
  """Rounds `x` to `digits` decimals (negative: to tens, hundreds...), halves away from zero."""
  factor = 10.0 ** digits
  scaled = abs(x) * factor
  rounded = math.floor(scaled + 0.5 + 1e-9) / factor
  return math.copysign(rounded, x) if rounded != 0 else 0.0


def fn_round(ev, args):
  arity(args, 1, 2)
  x = to_number(ev.value(args[0]))
  digits = int(to_number(ev.value(args[1]))) if len(args) > 1 else 0
  digits = max(-15, min(15, digits))
  return round_half_away(x, digits)


def fn_abs(ev, args):
  arity(args, 1, 1)
  return abs(to_number(ev.value(args[0])))


def fn_mod(ev, args):
  arity(args, 2, 2)
  a = to_number(ev.value(args[0]))
  b = to_number(ev.value(args[1]))
  if b == 0:
    fail(DIV_ZERO)
  return a - b * math.floor(a / b)


def fn_if(ev, args):
  arity(args, 2, 3)
  if to_bool(ev.value(args[0])):
    return ev.value(args[1])
  return ev.value(args[2]) if len(args) == 3 else False


def fn_iferror(ev, args):
  arity(args, 2, 2)
  try:
    return ev.value(args[0])
  except FormulaError:
    return ev.value(args[1])


def fn_and(ev, args):
  arity(args, 1, 30)
  result = True
  for arg in args:
    result = to_bool(ev.value(arg)) and result
  return result


def fn_or(ev, args):
  arity(args, 1, 30)
  result = False
  for arg in args:
    result = to_bool(ev.value(arg)) or result
  return result


def fn_not(ev, args):
  arity(args, 1, 1)
  return not to_bool(ev.value(args[0]))


def fn_len(ev, args):
  arity(args, 1, 1)
  return float(len(to_text(ev.value(args[0]))))


def fn_concat(ev, args):
  return "".join(to_text(ev.value(arg)) for arg in args)


def parse_criterion(criterion):
  """Splits a criterion such as ">=10" or "apples" into an operator and an operand value."""
  if isinstance(criterion, str):
    for op in ("<=", ">=", "<>", "<", ">", "="):
      if criterion.startswith(op):
        rest = criterion[len(op):]
        number = parse_number(rest)
        return op, (number if number is not None else rest)
    number = parse_number(criterion)
    return "=", (number if number is not None else criterion)
  return "=", criterion


def matches(value, op, operand):
  """Returns whether a cell value satisfies a parsed criterion; errors never match."""
  if isinstance(value, ErrorValue) or value is None:
    return False
  if isinstance(operand, float) and not isinstance(value, float):
    return op == "<>"
  return compare(op, value, operand)


def criterion_cells(ev, args):
  if not isinstance(args[0], Range):
    fail(VALUE)
  op, operand = parse_criterion(checked(ev.value(args[1])))
  return ev.range_values(args[0]), op, operand


def fn_countif(ev, args):
  arity(args, 2, 2)
  values, op, operand = criterion_cells(ev, args)
  return float(sum(1 for value in values if matches(value, op, operand)))


def fn_sumif(ev, args):
  arity(args, 2, 3)
  values, op, operand = criterion_cells(ev, args)
  targets = values
  if len(args) == 3:
    if not isinstance(args[2], Range):
      fail(VALUE)
    targets = ev.range_values(args[2])
  result = 0.0
  for value, target in zip(values, targets):
    if matches(value, op, operand) and isinstance(target, float):
      result += target
  return finite(result)


FUNCTIONS = {
  "SUM": fn_sum,
  "AVG": fn_average,
  "AVERAGE": fn_average,
  "MIN": fn_min,
  "MAX": fn_max,
  "COUNT": fn_count,
  "ROUND": fn_round,
  "ABS": fn_abs,
  "MOD": fn_mod,
  "IF": fn_if,
  "IFERROR": fn_iferror,
  "AND": fn_and,
  "OR": fn_or,
  "NOT": fn_not,
  "LEN": fn_len,
  "CONCAT": fn_concat,
  "COUNTIF": fn_countif,
  "SUMIF": fn_sumif,
}
