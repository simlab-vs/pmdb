"""Mutation of Python sources at sites enumerated mechanically inside function bodies."""

import ast
import copy

COMPARE_SWAPS = {
  ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
  ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
BINOP_SWAPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.FloorDiv: ast.Mod, ast.Mod: ast.FloorDiv}
BOOLOP_SWAPS = {ast.And: ast.Or, ast.Or: ast.And}


def enclosing_functions(tree):
  """Maps the id of every node inside a function body to the qualified name of that function."""
  owners = {}

  def visit(node, scope):
    for child in ast.iter_child_nodes(node):
      if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
        name = f"{scope}.{child.name}" if scope else child.name
        for n in ast.walk(child):
          owners.setdefault(id(n), name)
        visit(child, name)
      elif isinstance(child, ast.ClassDef):
        visit(child, f"{scope}.{child.name}" if scope else child.name)
      else:
        visit(child, scope)

  visit(tree, "")
  return owners


def inside_fstring(tree):
  ids = set()
  for node in ast.walk(tree):
    if isinstance(node, ast.JoinedStr):
      ids.update(id(n) for n in ast.walk(node))
  return ids


def sites(source):
  """Returns the mutation sites of `source` as `(node index, operator, description)` triples."""
  tree = ast.parse(source)
  owners = enclosing_functions(tree)
  excluded = inside_fstring(tree)
  result = []
  for index, node in enumerate(ast.walk(tree)):
    if id(node) not in owners or id(node) in excluded or not hasattr(node, "lineno"):
      continue
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE_SWAPS:
      result.append((index, "compare", f"{type(node.ops[0]).__name__} -> "
                     f"{COMPARE_SWAPS[type(node.ops[0])].__name__}"))
    elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_SWAPS:
      result.append((index, "binop", f"{type(node.op).__name__} -> "
                     f"{BINOP_SWAPS[type(node.op)].__name__}"))
    elif isinstance(node, ast.BoolOp):
      result.append((index, "boolop", f"{type(node.op).__name__} -> "
                     f"{BOOLOP_SWAPS[type(node.op)].__name__}"))
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
      result.append((index, "drop-not", "not x -> x"))
    elif (isinstance(node, ast.Constant) and type(node.value) is int):
      result.append((index, "const+1", f"{node.value} -> {node.value + 1}"))
      result.append((index, "const-1", f"{node.value} -> {node.value - 1}"))
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
      if node.func.id in ("min", "max"):
        result.append((index, "minmax", f"{node.func.id} -> {'max' if node.func.id == 'min' else 'min'}"))
      elif len(node.args) >= 2 and not any(isinstance(a, ast.Starred) for a in node.args):
        result.append((index, "swap-args", f"swap arguments of {node.func.id}"))
  return result


def mutated_node(node, operator):
  node = copy.deepcopy(node)
  if operator == "compare":
    node.ops = [COMPARE_SWAPS[type(node.ops[0])]()]
  elif operator == "binop":
    node.op = BINOP_SWAPS[type(node.op)]()
  elif operator == "boolop":
    node.op = BOOLOP_SWAPS[type(node.op)]()
  elif operator == "drop-not":
    node = node.operand
  elif operator == "const+1":
    node.value += 1
  elif operator == "const-1":
    node.value -= 1
  elif operator == "minmax":
    node.func.id = "max" if node.func.id == "min" else "min"
  elif operator == "swap-args":
    node.args[0], node.args[1] = node.args[1], node.args[0]
  return node


def apply(source, index, operator):
  """Returns `(mutated source, function, line)`, changing only the text of the mutated node."""
  tree = ast.parse(source)
  owners = enclosing_functions(tree)
  node = list(ast.walk(tree))[index]
  replacement = ast.unparse(mutated_node(node, operator))
  if isinstance(node, ast.Constant) and node.value < 0 or operator == "drop-not":
    replacement = f"({replacement})" if operator != "drop-not" else replacement

  lines = source.splitlines(keepends=True)
  offsets = [0]
  for l in lines:
    offsets.append(offsets[-1] + len(l.encode()))
  data = source.encode()
  start = offsets[node.lineno - 1] + node.col_offset
  end = offsets[node.end_lineno - 1] + node.end_col_offset
  original = data[start:end].decode()
  if original.startswith("(") and not replacement.startswith("("):
    replacement = f"({replacement})"
  mutated = (data[:start] + replacement.encode() + data[end:]).decode()
  ast.parse(mutated)
  return mutated, owners[id(node)], node.lineno, original, replacement
