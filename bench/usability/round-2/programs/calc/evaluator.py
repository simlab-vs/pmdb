"""Evaluates calculator programs.

Values are integers, closures and builtins. Truthiness follows integers: 0 is false and any other
integer is true. Division and remainder round toward zero, like in C.
"""


class EvalError(Exception):
  pass


class Closure:

  def __init__(self, parameters, body, environment):
    self.parameters = parameters
    self.body = body
    self.environment = environment


def divide(a, b):
  """Returns `a / b` rounded toward zero."""
  if b == 0:
    raise EvalError("division by zero")
  q = abs(a) // abs(b)
  return q if (a >= 0) == (b >= 0) else -q


def remainder(a, b):
  """Returns the remainder of `a / b`, which has the sign of `a`."""
  return a - b * divide(a, b)


def binary(op, a, b):
  """Applies the binary operator `op` to integers `a` and `b`."""
  if op == "+":
    return a + b
  if op == "-":
    return a - b
  if op == "*":
    return a * b
  if op == "/":
    return divide(a, b)
  if op == "%":
    return remainder(a, b)
  if op == "==":
    return int(a == b)
  if op == "!=":
    return int(a != b)
  if op == "<":
    return int(a < b)
  if op == "<=":
    return int(a <= b)
  if op == ">":
    return int(a > b)
  if op == ">=":
    return int(a >= b)
  raise EvalError(f"unknown operator {op}")


BUILTINS = {
  "abs": lambda x: abs(x),
  "min": lambda *xs: min(xs),
  "max": lambda *xs: max(xs),
  "gcd": lambda a, b: gcd(a, b),
}


def gcd(a, b):
  a, b = abs(a), abs(b)
  while b != 0:
    a, b = b, a % b
  return a


def lookup(environment, name):
  """Returns the value bound to `name` in `environment`, a chain of `(name, value, parent)`."""
  while environment is not None:
    n, v, environment = environment
    if n == name:
      return v
  if name in BUILTINS:
    return BUILTINS[name]
  raise EvalError(f"undefined name {name}")


def apply(callee, arguments, depth):
  """Applies `callee` to `arguments`."""
  if callable(callee):
    return callee(*arguments)
  if not isinstance(callee, Closure):
    raise EvalError("call of a non-function")
  if len(arguments) != len(callee.parameters):
    raise EvalError(f"expected {len(callee.parameters)} arguments, got {len(arguments)}")
  environment = callee.environment
  for p, a in zip(callee.parameters, arguments):
    environment = (p, a, environment)
  return evaluate(callee.body, environment, depth + 1)


def evaluate(tree, environment=None, depth=0):
  """Returns the value of `tree` in `environment`."""
  if depth > 200:
    raise EvalError("recursion too deep")
  kind = tree[0]
  if kind == "int":
    return tree[1]
  if kind == "var":
    return lookup(environment, tree[1])
  if kind == "unary":
    v = evaluate(tree[2], environment, depth)
    return -v if tree[1] == "-" else int(v == 0)
  if kind == "binary":
    op = tree[1]
    a = evaluate(tree[2], environment, depth)
    if op == "&&":
      return int(a != 0 and evaluate(tree[3], environment, depth) != 0)
    if op == "||":
      return int(a != 0 or evaluate(tree[3], environment, depth) != 0)
    return binary(op, a, evaluate(tree[3], environment, depth))
  if kind == "let":
    _, name, value, body = tree
    if value[0] == "fn":
      # Functions bound by `let` can refer to themselves.
      closure = Closure(value[1], value[2], None)
      closure.environment = (name, closure, environment)
      return evaluate(body, closure.environment, depth)
    return evaluate(body, (name, evaluate(value, environment, depth), environment), depth)
  if kind == "if":
    if evaluate(tree[1], environment, depth) != 0:
      return evaluate(tree[2], environment, depth)
    return evaluate(tree[3], environment, depth)
  if kind == "fn":
    return Closure(tree[1], tree[2], environment)
  if kind == "call":
    callee = evaluate(tree[1], environment, depth)
    arguments = [evaluate(a, environment, depth) for a in tree[2]]
    return apply(callee, arguments, depth)
  raise EvalError(f"unknown tree {kind}")
