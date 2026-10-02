"""Tokenizer and parser of spreadsheet formulas.

A formula such as `=SUM(A1:B3)*2 + Data!C4` is turned into a tree of nodes. Cell references keep
the sheet they name, or None for the sheet of the cell that holds the formula.
"""

# Grid limits: columns A to Z and rows 1 to MAX_ROW.
MAX_COLUMN = 26
MAX_ROW = 99

# Binary operators by precedence level, from the loosest binding.
COMPARISONS = ("=", "<>", "<", ">", "<=", ">=")
LEVELS = [COMPARISONS, ("&",), ("+", "-"), ("*", "/")]

TWO_CHAR_OPERATORS = ("<>", "<=", ">=")
ONE_CHAR_OPERATORS = "+-*/^&=<>%"


class FormulaSyntaxError(Exception):
  pass


class Token:
  __slots__ = ("kind", "text", "pos")

  def __init__(self, kind, text, pos):
    self.kind = kind
    self.text = text
    self.pos = pos


def column_number(letters):
  """Returns the 1-based number of the column named `letters` (A is 1, Z is 26, AA is 27)."""
  number = 0
  for ch in letters:
    number = number * 26 + (ord(ch) - ord("A") + 1)
  return number


def column_letters(number):
  letters = ""
  while number > 0:
    number, rest = divmod(number - 1, 26)
    letters = chr(ord("A") + rest) + letters
  return letters


def split_address(text):
  """Splits a cell address like `B12` into its column and row numbers, or returns None."""
  i = 0
  while i < len(text) and text[i].isalpha():
    i += 1
  letters, digits = text[:i], text[i:]
  if not letters or not digits or not digits.isdigit() or not letters.isupper():
    return None
  return column_number(letters), int(digits)


def format_address(column, row):
  return f"{column_letters(column)}{row}"


def scan_number(text, start):
  """Returns the end of the number literal starting at `start`."""
  i = start
  while i < len(text) and text[i].isdigit():
    i += 1
  if i < len(text) and text[i] == ".":
    i += 1
    while i < len(text) and text[i].isdigit():
      i += 1
  return i


def tokenize(text):
  """Splits the formula `text` (without its leading '=') into tokens."""
  tokens = []
  i = 0
  while i < len(text):
    ch = text[i]
    if ch.isspace():
      i += 1
    elif ch.isdigit() or (ch == "." and i + 1 < len(text) and text[i + 1].isdigit()):
      end = scan_number(text, i)
      tokens.append(Token("number", text[i:end], i))
      i = end
    elif ch == '"':
      end = text.find('"', i + 1)
      if end < 0:
        raise FormulaSyntaxError(f"unterminated string at {i}")
      tokens.append(Token("string", text[i + 1:end], i))
      i = end + 1
    elif ch.isalpha() or ch == "_":
      end = i
      while end < len(text) and (text[end].isalnum() or text[end] in "_."):
        end += 1
      word = text[i:end]
      if end < len(text) and text[end] == "!":
        tokens.append(Token("sheet", word, i))
        end += 1
      elif split_address(word) is not None:
        tokens.append(Token("ref", word, i))
      else:
        tokens.append(Token("name", word.upper(), i))
      i = end
    elif text[i:i + 2] in TWO_CHAR_OPERATORS:
      tokens.append(Token("op", text[i:i + 2], i))
      i += 2
    elif ch in ONE_CHAR_OPERATORS:
      tokens.append(Token("op", ch, i))
      i += 1
    elif ch in "(),:":
      tokens.append(Token(ch, ch, i))
      i += 1
    else:
      raise FormulaSyntaxError(f"unexpected character {ch!r} at {i}")
  tokens.append(Token("end", "", len(text)))
  return tokens


# -- Syntax tree ---------------------------------------------------------------------------------

class Number:
  def __init__(self, value):
    self.value = value


class Text:
  def __init__(self, value):
    self.value = value


class Boolean:
  def __init__(self, value):
    self.value = value


class Ref:
  """A reference to one cell; `sheet` is None for the sheet holding the formula."""

  def __init__(self, sheet, column, row):
    self.sheet = sheet
    self.column = column
    self.row = row


class Range:
  """A rectangular block of cells, with its corners normalised to top-left and bottom-right."""

  def __init__(self, sheet, first, last):
    self.sheet = sheet
    self.left = min(first[0], last[0])
    self.right = max(first[0], last[0])
    self.top = min(first[1], last[1])
    self.bottom = max(first[1], last[1])

  def cells(self):
    """Yields the (column, row) pairs of the range inside the grid, row by row."""
    for row in range(self.top, min(self.bottom, MAX_ROW) + 1):
      for column in range(self.left, min(self.right, MAX_COLUMN) + 1):
        yield column, row


class Unary:
  def __init__(self, op, operand):
    self.op = op
    self.operand = operand


class Percent:
  def __init__(self, operand):
    self.operand = operand


class Binary:
  def __init__(self, op, left, right):
    self.op = op
    self.left = left
    self.right = right


class Call:
  def __init__(self, name, args):
    self.name = name
    self.args = args


class Parser:
  """A recursive descent parser over the tokens of one formula."""

  def __init__(self, tokens):
    self.tokens = tokens
    self.pos = 0

  def peek(self):
    return self.tokens[self.pos]

  def advance(self):
    token = self.tokens[self.pos]
    self.pos += 1
    return token

  def expect(self, kind):
    token = self.advance()
    if token.kind != kind:
      raise FormulaSyntaxError(f"expected {kind} at {token.pos}, found {token.text!r}")
    return token

  def at_op(self, ops):
    token = self.peek()
    return token.kind == "op" and token.text in ops

  def parse(self):
    node = self.binary(0)
    if self.peek().kind != "end":
      raise FormulaSyntaxError(f"unexpected {self.peek().text!r} at {self.peek().pos}")
    return node

  def binary(self, level):
    """Parses a left-associative chain of the operators of `LEVELS[level]`."""
    if level == len(LEVELS):
      return self.power()
    node = self.binary(level + 1)
    while self.at_op(LEVELS[level]):
      op = self.advance().text
      node = Binary(op, node, self.binary(level + 1))
    return node

  def power(self):
    """Parses `^`, which binds tighter than the arithmetic operators and associates left."""
    node = self.unary()
    while self.at_op(("^",)):
      self.advance()
      node = Binary("^", node, self.unary())
    return node

  def unary(self):
    if self.at_op(("-", "+")):
      op = self.advance().text
      return Unary(op, self.unary())
    return self.postfix()

  def postfix(self):
    node = self.primary()
    while self.at_op(("%",)):
      self.advance()
      node = Percent(node)
    return node

  def primary(self):
    token = self.advance()
    if token.kind == "number":
      return Number(float(token.text))
    if token.kind == "string":
      return Text(token.text)
    if token.kind == "(":
      node = self.binary(0)
      self.expect(")")
      return node
    if token.kind == "sheet":
      return self.reference(token.text, self.expect("ref"))
    if token.kind == "ref":
      return self.reference(None, token)
    if token.kind == "name":
      if token.text in ("TRUE", "FALSE") and self.peek().kind != "(":
        return Boolean(token.text == "TRUE")
      return self.call(token.text)
    raise FormulaSyntaxError(f"unexpected {token.text!r} at {token.pos}")

  def reference(self, sheet, token):
    first = split_address(token.text)
    if self.peek().kind != ":":
      return Ref(sheet, first[0], first[1])
    self.advance()
    last = split_address(self.expect("ref").text)
    return Range(sheet, first, last)

  def call(self, name):
    self.expect("(")
    args = []
    if self.peek().kind != ")":
      args.append(self.binary(0))
      while self.peek().kind == ",":
        self.advance()
        args.append(self.binary(0))
    self.expect(")")
    return Call(name, args)


def parse_formula(text):
  """Parses the formula `text`, given without its leading '='."""
  return Parser(tokenize(text)).parse()


def references(node, sheet):
  """Returns the (sheet, column, row) cells read by `node`, for a formula held on `sheet`."""
  found = []
  stack = [node]
  while stack:
    current = stack.pop()
    if isinstance(current, Ref):
      found.append((current.sheet or sheet, current.column, current.row))
    elif isinstance(current, Range):
      target = current.sheet or sheet
      found.extend((target, column, row) for column, row in current.cells())
    elif isinstance(current, (Unary, Percent)):
      stack.append(current.operand)
    elif isinstance(current, Binary):
      stack.append(current.right)
      stack.append(current.left)
    elif isinstance(current, Call):
      stack.extend(reversed(current.args))
  return found
