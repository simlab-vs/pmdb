"""Mutation operators modelling realistic bugs, in addition to those of round 1.

Round 1's operators flip operators and constants, which leaves a visible oddity at the mutated
site. These operators produce code that reads naturally:

- `wrong-var`: a variable read is replaced by another local variable of the same function, as
  when the wrong one of two similar names is used;
- `no-copy`: a copy (`list(x)`, `dict(x)`, `set(x)`, `x.copy()`, `copy.copy(x)`) is replaced by
  the original, so that later mutations are shared;
- `get-default`: the integer default of `d.get(k, n)` is replaced by `n + 1`;
- `drop-update`: an augmented assignment (`total += x`) is removed;
- `break-continue`: `break` and `continue` are exchanged;
- `range-end`: the end of a `range` whose end isn't a constant is decreased by one.
"""

import ast

from pmdbbench import mutation

COPY_FUNCTIONS = {"list", "dict", "set"}
ROUND_1_OPERATORS = {
  "compare", "binop", "boolop", "drop-not", "const+1", "const-1", "minmax", "swap-args"}


def local_names(function):
  """Returns the parameters and the names assigned in `function`, excluding nested functions."""
  names = {a.arg for a in function.args.args + function.args.kwonlyargs + function.args.posonlyargs}
  todo = list(function.body)
  while todo:
    node = todo.pop()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
      continue
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
      names.add(node.id)
    todo.extend(ast.iter_child_nodes(node))
  return names - {"self", "cls", "_"}


def functions_by_node(tree):
  """Maps the id of every node inside a function to the innermost function containing it."""
  result = {}
  for f in ast.walk(tree):
    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
      for n in ast.walk(f):
        result[id(n)] = f  # Inner functions are visited later and override their parents.
  return result


def is_copy(node):
  if not isinstance(node, ast.Call) or node.keywords:
    return False
  if isinstance(node.func, ast.Name) and node.func.id in COPY_FUNCTIONS and len(node.args) == 1:
    return not isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp, ast.Starred))
  if isinstance(node.func, ast.Attribute) and not node.args:
    if node.func.attr == "copy":
      return True
  if (isinstance(node.func, ast.Attribute) and node.func.attr == "copy"
      and isinstance(node.func.value, ast.Name) and node.func.value.id == "copy"
      and len(node.args) == 1):
    return True
  return False


def realistic_sites(source):
  """Returns the sites of the operators of this module as `(index, operator, argument, description)`."""
  tree = ast.parse(source)
  owners = mutation.enclosing_functions(tree)
  excluded = mutation.inside_fstring(tree)
  functions = functions_by_node(tree)
  result = []
  for index, node in enumerate(ast.walk(tree)):
    if id(node) not in owners or id(node) in excluded or not hasattr(node, "lineno"):
      continue
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
      f = functions[id(node)]
      names = local_names(f)
      if node.id in names:
        for other in sorted(names - {node.id}):
          result.append((index, "wrong-var", other, f"{node.id} -> {other}"))
    elif is_copy(node):
      result.append((index, "no-copy", None, f"{ast.unparse(node)} -> original"))
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and node.func.attr == "get" and len(node.args) == 2
          and isinstance(node.args[1], ast.Constant) and type(node.args[1].value) is int):
      v = node.args[1].value
      result.append((index, "get-default", None, f"default {v} -> {v + 1}"))
    elif isinstance(node, ast.AugAssign):
      result.append((index, "drop-update", None, f"remove `{ast.unparse(node)}`"))
    elif isinstance(node, (ast.Break, ast.Continue)):
      a, b = ("break", "continue") if isinstance(node, ast.Break) else ("continue", "break")
      result.append((index, "break-continue", None, f"{a} -> {b}"))
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
          and node.func.id == "range" and 1 <= len(node.args) <= 3
          and not isinstance(node.args[min(len(node.args), 2) - 1], ast.Constant)):
      result.append((index, "range-end", None, "end -> end - 1"))
  return result


def sites(source):
  """Returns every site of `source`, of round 1's operators and of this module's, as
  `(index, operator, argument, description)`."""
  return ([(i, o, None, d) for i, o, d in mutation.sites(source)] + realistic_sites(source))


def replacement(node, operator, argument):
  if operator == "wrong-var":
    return argument
  if operator == "no-copy":
    copied = node.args[0] if node.args else node.func.value
    text = ast.unparse(copied)
    return text if isinstance(copied, (ast.Name, ast.Attribute, ast.Subscript)) else f"({text})"
  if operator == "get-default":
    args = [ast.unparse(node.args[0]), str(node.args[1].value + 1)]
    return f"{ast.unparse(node.func)}({', '.join(args)})"
  if operator == "drop-update":
    return "pass"
  if operator == "break-continue":
    return "continue" if isinstance(node, ast.Break) else "break"
  if operator == "range-end":
    args = [ast.unparse(a) for a in node.args]
    end = 1 if len(args) > 1 else 0
    args[end] = f"{args[end]} - 1"
    return f"range({', '.join(args)})"
  raise ValueError(operator)


def apply(source, index, operator, argument):
  """Returns `(mutated source, function, line, original text, replacement text)`."""
  if operator in ROUND_1_OPERATORS:
    return mutation.apply(source, index, operator)
  tree = ast.parse(source)
  owners = mutation.enclosing_functions(tree)
  node = list(ast.walk(tree))[index]
  text = replacement(node, operator, argument)
  lines = source.splitlines(keepends=True)
  offsets = [0]
  for l in lines:
    offsets.append(offsets[-1] + len(l.encode()))
  data = source.encode()
  start = offsets[node.lineno - 1] + node.col_offset
  end = offsets[node.end_lineno - 1] + node.end_col_offset
  original = data[start:end].decode()
  mutated = (data[:start] + text.encode() + data[end:]).decode()
  ast.parse(mutated)
  return mutated, owners[id(node)], node.lineno, original, text
