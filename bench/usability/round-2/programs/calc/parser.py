"""Parses calculator programs into trees made of tuples.

Trees have the following shapes:
- ("int", value)
- ("var", name)
- ("unary", op, operand)
- ("binary", op, lhs, rhs)
- ("let", name, value, body)
- ("if", condition, success, failure)
- ("fn", parameters, body)
- ("call", callee, arguments)
"""

from lexer import tokenize

# Binding power of binary operators; all are left-associative.
PRECEDENCE = {
  "||": 1, "&&": 2,
  "==": 3, "!=": 3,
  "<": 4, "<=": 4, ">": 4, ">=": 4,
  "+": 5, "-": 5,
  "*": 6, "/": 6, "%": 6,
}


class ParseError(Exception):
  pass


class Parser:

  def __init__(self, source):
    self.tokens = tokenize(source)
    self.index = 0

  def peek(self):
    return self.tokens[self.index]

  def take(self, kind, text=None):
    """Consumes and returns the next token iff it has the given kind and text."""
    t = self.peek()
    if t[0] == kind and (text is None or t[1] == text):
      self.index += 1
      return t
    return None

  def expect(self, kind, text=None):
    t = self.take(kind, text)
    if t is None:
      found = self.peek()
      raise ParseError(f"expected {text or kind} at {found[2]}, found {found[1]!r}")
    return t

  def parse_program(self):
    tree = self.parse_expression()
    self.expect("end")
    return tree

  def parse_expression(self):
    if self.take("keyword", "let"):
      name = self.expect("name")[1]
      self.expect("op", "=")
      value = self.parse_expression()
      self.expect("keyword", "in")
      return ("let", name, value, self.parse_expression())
    if self.take("keyword", "if"):
      condition = self.parse_expression()
      self.expect("keyword", "then")
      success = self.parse_expression()
      self.expect("keyword", "else")
      return ("if", condition, success, self.parse_expression())
    if self.take("keyword", "fn"):
      self.expect("op", "(")
      parameters = []
      if not self.take("op", ")"):
        parameters.append(self.expect("name")[1])
        while self.take("op", ","):
          parameters.append(self.expect("name")[1])
        self.expect("op", ")")
      return ("fn", tuple(parameters), self.parse_expression())
    return self.parse_binary(1)

  def parse_binary(self, minimum):
    """Parses a sequence of binary operations whose operators bind at least as `minimum`."""
    lhs = self.parse_unary()
    while True:
      t = self.peek()
      precedence = PRECEDENCE.get(t[1]) if t[0] == "op" else None
      if precedence is None or precedence < minimum:
        return lhs
      self.index += 1
      rhs = self.parse_binary(precedence + 1)
      lhs = ("binary", t[1], lhs, rhs)

  def parse_unary(self):
    if self.take("op", "-"):
      return ("unary", "-", self.parse_unary())
    if self.take("op", "!"):
      return ("unary", "!", self.parse_unary())
    return self.parse_postfix()

  def parse_postfix(self):
    tree = self.parse_primary()
    while self.take("op", "("):
      arguments = []
      if not self.take("op", ")"):
        arguments.append(self.parse_expression())
        while self.take("op", ","):
          arguments.append(self.parse_expression())
        self.expect("op", ")")
      tree = ("call", tree, tuple(arguments))
    return tree

  def parse_primary(self):
    if t := self.take("int"):
      return ("int", int(t[1]))
    if t := self.take("name"):
      return ("var", t[1])
    if self.take("op", "("):
      tree = self.parse_expression()
      self.expect("op", ")")
      return tree
    found = self.peek()
    raise ParseError(f"expected an expression at {found[2]}, found {found[1]!r}")


def parse(source):
  """Returns the tree of the program in `source`."""
  return Parser(source).parse_program()
