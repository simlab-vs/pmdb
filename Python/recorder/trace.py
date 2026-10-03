"""Reading traces written by the recorder, and querying them in Python.

    import recorder
    from recorder import Q
    t = recorder.load("trace.pmdb")
    t.functions()                                   # each recorded function and its number of calls
    bad = t.calls("ship", raised="AssertionError").first()
    bad["order"], bad.caller, bad.path()            # an argument by name, the calling call, the stack
    t.calls("deposit", before=bad, where=lambda c: c["account"] == bad["account"])
    t.calls("post", caller=Q("close_month", where=lambda c: c["day"] == 31))
    t.calls("post").count_by(lambda c: c["account"])

A trace is a tree of calls in recording order. `Trace.calls` selects calls by function and
conditions; a selection (`Calls`) is a list of calls in recording order, which can be filtered
further, combined and summarized. Values are Python values: `None`, Booleans, integers, floats,
strings, lists (arrays, including tuples) and dicts (tables, including named tuples), plus
`Function` for functions and `Opaque` for other objects.

Selectors. Wherever a selection of calls is expected (the positional arguments of `calls` and
`where`, and the conditions relating calls), any of these can be given:
- a string: calls of the function with that name, or whose qualified name ends with it after a
  dot (`"post"` and `"Ledger.post"` both match `Ledger.post`);
- a compiled regular expression, matching the whole qualified name;
- a predicate on calls (a function taking a `Call` and returning a Boolean);
- a `Call`, or a collection of calls such as a `Calls`;
- a `Q`, which combines a selector with conditions, and can be combined with `&`, `|` and `~`.

Conditions (keyword arguments of `calls`, `where` and `Q`):
- `where=predicate`: the predicate holds for the call;
- `returned=`: `True` (the call returned), `False` (it didn't), a predicate on the value it
  returned, or a value equal to it;
- `raised=`: `True`, `False`, the name of the exception's type (or the type), or a predicate on the
  exception (a `Raised`, with `type` and `message`);
- `caller=`, `callee=`: the calling call, or one of the calls it made directly, is selected;
- `ancestor=`, `descendant=`: one of the calls in which it was made, directly or not, or one of the
  calls made during it, directly or not, is selected;
- `before=`, `after=`: it started before a selected call started, or after a selected call ended
  (a generator's call ends when it finishes, not when it yields).
"""

import collections
import difflib
import pickle
import pickletools
import re
import struct


class QueryError(Exception):
  """An error in a query, such as a predicate raising on a call."""


class Opaque(object):
  """An object the recorder couldn't record as a value: its pickle, or a description of it."""

  __slots__ = ("pickled", "description")

  def __init__(self, pickled=None, description=None):
    self.pickled = pickled
    self.description = description

  @property
  def type(self):
    """The qualified name of the object's class (`module.Class`), if known."""
    if self.pickled is None:
      return None
    try:
      strings = []
      for op, arg, _ in pickletools.genops(self.pickled):
        if op.name in ("GLOBAL", "INST"):
          return arg.replace(" ", ".")
        if isinstance(arg, str):
          strings.append(arg)
        if op.name == "STACK_GLOBAL" and len(strings) >= 2:
          return f"{strings[-2]}.{strings[-1]}"
    except Exception:
      pass
    return None

  def unpickle(self):
    """Returns the object, unpickled. This imports the program's modules, which must be
    importable (e.g., with the program's directory on `sys.path`), and runs their code."""
    if self.pickled is None:
      raise ValueError(f"no pickle recorded for {self.description}")
    return pickle.loads(self.pickled)

  def __repr__(self):
    if self.description is not None:
      return self.description
    return f"<{self.type or 'object'} object; .unpickle() rebuilds it>"

  def __eq__(self, other):
    return isinstance(other, Opaque) and (self.pickled, self.description) == (
      other.pickled, other.description)

  def __hash__(self):
    return hash((self.pickled, self.description))


class Function(str):
  """A function, recorded by its qualified name."""

  def __repr__(self):
    return f"<function {str(self)}>"


class Raised(dict):
  """The exception a call raised: a dict with its `type` and `message`."""

  @property
  def type(self):
    return self.get("type")

  @property
  def message(self):
    return self.get("message")

  def __repr__(self):
    return f"{self.type}({self.message!r})"


class Reader(object):
  """Decodes the archive written by `recorder.archive.Archive`."""

  def __init__(self, data):
    self.data = memoryview(data)
    self.i = 0

  def byte(self):
    b = self.data[self.i]
    self.i += 1
    return b

  def bytes(self, n):
    b = bytes(self.data[self.i:self.i + n])
    self.i += n
    return b

  def unsigned(self):
    result = shift = 0
    while True:
      b = self.data[self.i]
      self.i += 1
      result |= (b & 0x7f) << shift
      shift += 7
      if not b & 0x80:
        return result

  def signed(self):
    result = shift = 0
    while True:
      b = self.data[self.i]
      self.i += 1
      result |= (b & 0x7f) << shift
      shift += 7
      if not b & 0x80:
        if b & 0x40:
          result -= 1 << shift
        return result

  def string(self):
    n = self.unsigned()
    s = str(self.data[self.i:self.i + n], "utf-8")
    self.i += n
    return s

  def value(self):
    tag = self.byte()
    if tag == 0x00:
      return None
    if tag == 0x01:
      return self.signed()
    if tag == 0x02:
      x = struct.unpack_from("<d", self.data, self.i)[0]
      self.i += 8
      return x
    if tag == 0x03:
      return self.string()
    if tag == 0x04:
      return [self.value() for _ in range(self.unsigned())]
    if tag == 0x05:
      n = self.unsigned()
      return {self.string(): self.value() for _ in range(n)}
    if tag == 0x06:
      return bool(self.byte())
    if tag == 0xfe:
      return Function(self.string())
    if tag == 0xff:
      return Opaque(pickled=self.bytes(self.unsigned()))
    raise ValueError(f"unknown value tag {tag:#x} at offset {self.i - 1}")


def _no_attribute(obj, name):
  """Raises the `AttributeError` for reading `name` from `obj`, suggesting close names."""
  names = [n for n in dir(type(obj)) if not n.startswith("_")]
  close = difflib.get_close_matches(name, names, n=3, cutoff=0.5)
  hint = f"; did you mean {', '.join(close)}?" if close else f"; it has {', '.join(names)}"
  raise AttributeError(f"{type(obj).__name__} has no attribute {name!r}{hint}")


def _short(value, n):
  if isinstance(value, Opaque) and value.description is None:
    return f"<{(value.type or 'object').rsplit('.', 1)[-1]}>"
  text = repr(value)
  return text if len(text) <= n else text[:n - 15] + " … " + text[-10:]


class Call(object):
  """A recorded call: its function, its arguments as they were when it started, its outcome and
  its place in the tree of calls."""

  __slots__ = ("trace", "index", "location", "function", "definition", "args", "names",
               "kwargs", "parent_index", "children_indices", "finish", "_outcome", "end_location",
               "depth", "snap_indices")

  def __init__(self, trace, index, location, function, definition, args, names, kwargs,
               parent_index, depth):
    self.trace = trace
    self.index = index            # position in recording order (of all observations)
    self.location = location      # (file, line) of the call site
    self.function = function      # qualified name, e.g. `Ledger.post`
    self.definition = definition  # (file, line) of the function's definition, if recorded
    self.args = args              # positional arguments (a method's `self` first)
    self.names = names            # the parameter receiving each positional argument, if recorded
    self.kwargs = kwargs          # named arguments
    self.parent_index = parent_index
    self.children_indices = []
    self.snap_indices = []
    self.finish = index           # index of the observation recording its end (see `load`)
    self._outcome = None          # ("returned", value) or ("raised", Raised)
    self.end_location = None      # (file, line) where the call returned or raised, if recorded
    self.depth = depth

  def __getattr__(self, name):
    _no_attribute(self, name)

  # Arguments.

  @property
  def params(self):
    """A dict from each parameter's name to its argument; the arguments collected by `*rest` are
    a list named `rest`, and those collected by `**kw` are under their own names."""
    result = {}
    for k, a in zip(self.names or (), self.args):
      if k.startswith("*"):
        result.setdefault(k[1:], []).append(a)
      elif k:
        result[k] = a
    result.update(self.kwargs)
    return result

  def __getitem__(self, key):
    """The positional argument at `key` if it's an integer, or the argument of the parameter
    named `key`."""
    if isinstance(key, int):
      return self.args[key]
    params = self.params
    if key not in params:
      raise KeyError(f"{key!r}: {self.function} has parameters {', '.join(params) or 'none'}")
    return params[key]

  def get(self, key, default=None):
    """The argument of the parameter named `key`, or `default`."""
    try:
      return self[key]
    except (KeyError, IndexError):
      return default

  @property
  def name(self):
    """The function's name, without its class or enclosing functions."""
    return self.function.rsplit(".", 1)[-1]

  # Outcome.

  @property
  def returned(self):
    """Whether the call returned (rather than raised, or not finishing)."""
    return self._outcome is not None and self._outcome[0] == "returned"

  @property
  def raised(self):
    """Whether the call raised an exception."""
    return self._outcome is not None and self._outcome[0] == "raised"

  @property
  def result(self):
    """The value the call returned, or `None` if it didn't return."""
    return self._outcome[1] if self.returned else None

  @property
  def exception(self):
    """The exception the call raised (a `Raised`, with `type` and `message`), or `None`."""
    return self._outcome[1] if self.raised else None

  # Relations.

  @property
  def caller(self):
    """The call during which this call was made, or `None` for calls made at the top level."""
    return self.trace._by_index.get(self.parent_index) if self.parent_index != self.index else None

  def callees(self, *selectors, **conditions):
    """The calls made directly during this call (that are selected, if arguments are given)."""
    return Calls(self.trace._by_index[i] for i in self.children_indices).where(
      *selectors, **conditions)

  def ancestors(self, *selectors, **conditions):
    """The calls during which this call was made, directly or not, innermost first (that are
    selected, if arguments are given)."""
    result, c = [], self.caller
    while c is not None:
      result.append(c)
      c = c.caller
    return Calls(result).where(*selectors, **conditions)

  def ancestor(self, *selectors, **conditions):
    """The innermost selected call during which this call was made, or `None`."""
    return self.ancestors(*selectors, **conditions).first()

  def descendants(self, *selectors, **conditions):
    """The calls made during this call, directly or not, in recording order (that are selected,
    if arguments are given)."""
    by_index, result, pending = self.trace._by_index, [], list(self.children_indices)
    while pending:
      i = pending.pop()
      result.append(i)
      pending.extend(by_index[i].children_indices)
    return Calls(by_index[i] for i in sorted(result)).where(*selectors, **conditions)

  def path(self):
    """The calls from the outermost one to this one."""
    return Calls(list(reversed(self.ancestors())) + [self])

  def snaps(self, label=None, deep=False):
    """The snaps taken directly during this call (or, if `deep`, during it or the calls it made),
    with `label` if given (a string or a compiled regular expression)."""
    if deep:
      inside = {self.index} | {c.index for c in self.descendants()}
      snaps = [s for s in self.trace._snaps if s.parent_index in inside]
    else:
      snaps = [self.trace._snaps_by_index[i] for i in self.snap_indices]
    return Snaps(snaps).labeled(label)

  def tree(self, depth=3, limit=50):
    """Prints this call and the calls made during it, up to `depth` levels and `limit` lines."""
    lines = []

    def visit(c, level):
      if len(lines) > limit:
        return
      lines.append("  " * level + c.describe())
      if level < depth:
        for d in c.callees():
          visit(d, level + 1)
      elif c.children_indices:
        lines.append("  " * (level + 1) + f"… {len(c.descendants())} calls")

    visit(self, 0)
    for line in lines[:limit]:
      print(line)
    if len(lines) > limit:
      print("…")

  # Description.

  def describe(self, width=160):
    """A one-line description of the call: its function, arguments and outcome."""
    names = self.names or [""] * len(self.args)
    parts, rest = [], {}
    for k, a in zip(names, self.args):
      if k.startswith("*"):
        rest.setdefault(k, []).append(a)
      else:
        parts.append((f"{k}=" if k else "") + _short(a, 60))
    parts += [f"{k}={_short(a, 60)}" for k, a in rest.items()]
    parts += [f"{k}={_short(a, 60)}" for k, a in self.kwargs.items()]
    text = f"#{self.index} {self.function}({', '.join(parts)})"
    if len(text) > width:
      text = text[:width - 20] + " … " + text[-15:]
    if self.returned:
      text += " -> " + _short(self.result, 80)
    elif self.raised:
      text += f" raised {self.exception.type}: {_short(self.exception.message, 80)}"
    return text

  def __repr__(self):
    return self.describe()

  def __eq__(self, other):
    return isinstance(other, Call) and other.trace is self.trace and other.index == self.index

  def __hash__(self):
    return hash(self.index)


class Snap(object):
  """A value recorded with a label, by `recorder.snap`."""

  __slots__ = ("trace", "index", "location", "label", "value", "parent_index")

  def __init__(self, trace, index, location, label, value, parent_index):
    self.trace, self.index, self.location, self.label = trace, index, location, label
    self.value, self.parent_index = value, parent_index

  @property
  def call(self):
    """The call during which the snap was taken, or `None` at the top level."""
    return self.trace._by_index.get(self.parent_index)

  def __repr__(self):
    return f"#{self.index} {self.location[0]}:{self.location[1]}: {self.label} = {_short(self.value, 120)}"


class Snaps(list):
  """A selection of snaps, in recording order."""

  def labeled(self, label):
    """The snaps with `label` (a string or a compiled regular expression), or all if `None`."""
    if label is None:
      return Snaps(self)
    if isinstance(label, re.Pattern):
      return Snaps(s for s in self if s.label is not None and label.fullmatch(s.label))
    return Snaps(s for s in self if s.label == label)

  def where(self, predicate):
    """The snaps for which `predicate` holds."""
    return Snaps(s for s in self if _holds(predicate, s, "where"))

  def values(self):
    return [s.value for s in self]

  def first(self):
    return self[0] if self else None

  def last(self):
    return self[-1] if self else None

  def show(self, limit=20):
    for s in self[:limit]:
      print(s)
    if len(self) > limit:
      print(f"… {len(self) - limit} more")


def _holds(predicate, item, role):
  """Returns `predicate(item)`, reporting an exception it raises with the item it raised on."""
  try:
    return predicate(item)
  except Exception as e:
    raise QueryError(
      f"the {role} predicate raised {type(e).__name__}: {e} on {item!r}; "
      "make it handle that case (e.g. `c.get(\"name\")`, or a test for `None`)") from e


class Q(object):
  """A reusable selection: a selector with conditions (see the module's documentation). Qs can be
  combined with `&` (both), `|` (either) and `~` (not)."""

  def __init__(self, *selectors, **conditions):
    for k in conditions:
      if k not in CONDITIONS:
        raise TypeError(f"unknown condition {k}=; the conditions are {', '.join(CONDITIONS)}")
    self.selectors, self.conditions = selectors, conditions
    self.combination = None

  @staticmethod
  def combine(op, operands):
    q = Q()
    q.combination = (op, operands)
    return q

  def __and__(self, other):
    return Q.combine("and", (self, other))

  def __or__(self, other):
    return Q.combine("or", (self, other))

  def __invert__(self):
    return Q.combine("not", (self,))

  def indices(self, trace):
    """The set of the indices of the calls of `trace` this selects."""
    cache = trace._selections
    key = id(self)
    if key not in cache:
      cache[key] = (self, self._indices(trace))  # `self` is kept so that its id isn't reused
    return cache[key][1]

  def _indices(self, trace):
    if self.combination is not None:
      op, operands = self.combination
      sets = [_indices(trace, x) for x in operands]
      if op == "and":
        return sets[0] & sets[1]
      if op == "or":
        return sets[0] | sets[1]
      return frozenset(trace._by_index_calls) - sets[0]
    tests = [_test(trace, s) for s in self.selectors] + [
      CONDITIONS[k](trace, v) for k, v in self.conditions.items()]
    return frozenset(c.index for c in trace._calls if all(t(c) for t in tests))

  def __repr__(self):
    if self.combination is not None:
      op, xs = self.combination
      return f"~{xs[0]!r}" if op == "not" else f"({xs[0]!r} {'&' if op == 'and' else '|'} {xs[1]!r})"
    args = [repr(s) for s in self.selectors] + [f"{k}={v!r}" for k, v in self.conditions.items()]
    return f"Q({', '.join(args)})"


def _name_matcher(name):
  suffix = "." + name
  return lambda f: f == name or f.endswith(suffix)


def _indices(trace, selector):
  """The set of the indices of the calls of `trace` selected by `selector`."""
  if isinstance(selector, Q):
    return selector.indices(trace)
  if isinstance(selector, Call):
    return frozenset([selector.index])
  if isinstance(selector, (str, re.Pattern)) or callable(selector):
    test = _test(trace, selector)
    return frozenset(c.index for c in trace._calls if test(c))
  try:
    items = list(selector)
  except TypeError:
    raise TypeError(f"can't select calls with {selector!r}") from None
  if not all(isinstance(c, Call) for c in items):
    raise TypeError(f"can't select calls with {selector!r}: it contains something else than calls")
  return frozenset(c.index for c in items)


def _test(trace, selector):
  """A predicate on the calls of `trace` testing whether they are selected by `selector`."""
  if isinstance(selector, str):
    match = _name_matcher(selector)
    if not any(match(f) for f in trace._functions):
      raise QueryError(f"no recorded function is named {selector!r}; see `functions()`")
    return lambda c: match(c.function)
  if isinstance(selector, re.Pattern):
    return lambda c: selector.fullmatch(c.function) is not None
  if isinstance(selector, Call):
    return lambda c: c.index == selector.index
  if isinstance(selector, Q):
    s = selector.indices(trace)
    return lambda c: c.index in s
  if callable(selector):
    return lambda c: bool(_holds(selector, c, "where"))
  s = _indices(trace, selector)
  return lambda c: c.index in s


def _returned(trace, value):
  if value is True or value is False:
    return lambda c: c.returned == value
  if callable(value):
    return lambda c: c.returned and bool(_holds(value, c.result, "returned"))
  return lambda c: c.returned and c.result == value


def _raised(trace, value):
  if value is True or value is False:
    return lambda c: c.raised == value
  if isinstance(value, type):
    value = value.__qualname__
  if isinstance(value, str):
    return lambda c: c.raised and c.exception.type == value
  return lambda c: c.raised and bool(_holds(value, c.exception, "raised"))


def _where(trace, predicate):
  return lambda c: bool(_holds(predicate, c, "where"))


def _caller(trace, selector):
  s = _indices(trace, selector)
  return lambda c: c.parent_index in s and c.parent_index != c.index


def _callee(trace, selector):
  s = _indices(trace, selector)
  return lambda c: any(i in s for i in c.children_indices)


def _ancestor(trace, selector):
  # The calls made during a selected call.
  inside, pending = set(), [i for i in _indices(trace, selector)]
  while pending:
    for j in trace._by_index[pending.pop()].children_indices:
      if j not in inside:
        inside.add(j)
        pending.append(j)
  return lambda c: c.index in inside


def _descendant(trace, selector):
  # The calls during which a selected call was made.
  enclosing = set()
  for i in _indices(trace, selector):
    p = trace._by_index[i].caller
    while p is not None and p.index not in enclosing:
      enclosing.add(p.index)
      p = p.caller
  return lambda c: c.index in enclosing


def _before(trace, selector):
  s = _indices(trace, selector)
  last = max(s, default=-1)
  return lambda c: c.index < last


def _after(trace, selector):
  s = _indices(trace, selector)
  first_end = min((trace._by_index[i].finish for i in s), default=None)
  return lambda c: first_end is not None and c.index > first_end


CONDITIONS = {
  "where": _where, "returned": _returned, "raised": _raised, "caller": _caller,
  "callee": _callee, "ancestor": _ancestor, "descendant": _descendant, "before": _before,
  "after": _after,
}


def _key(key):
  """A function on calls for `key`: a function, a parameter name or a position."""
  if callable(key):
    return key
  return lambda c: c[key]


class Calls(list):
  """A selection of calls, in recording order."""

  def __getattr__(self, name):
    _no_attribute(self, name)

  def where(self, *selectors, **conditions):
    """The calls selected by every selector and satisfying every condition (see the module's
    documentation)."""
    for k in conditions:
      if k not in CONDITIONS:
        raise TypeError(f"unknown condition {k}=; the conditions are {', '.join(CONDITIONS)}")
    if not selectors and not conditions or not self:
      return Calls(self)
    trace = self[0].trace
    tests = [_test(trace, s) for s in selectors]
    tests += [CONDITIONS[k](trace, v) for k, v in conditions.items()]
    return Calls(c for c in self if all(t(c) for t in tests))

  def __getitem__(self, key):
    result = list.__getitem__(self, key)
    return Calls(result) if isinstance(key, slice) else result

  # Combinations (results are in recording order).

  def __or__(self, other):
    seen = {c.index: c for c in self}
    seen.update((c.index, c) for c in other)
    return Calls(seen[i] for i in sorted(seen))

  def __and__(self, other):
    keep = {c.index for c in other}
    return Calls(c for c in self if c.index in keep)

  def __sub__(self, other):
    drop = {c.index for c in other}
    return Calls(c for c in self if c.index not in drop)

  # Summaries.

  def first(self):
    """The first call, or `None` if there is none."""
    return self[0] if self else None

  def last(self):
    """The last call, or `None` if there is none."""
    return self[-1] if self else None

  def one(self):
    """The only call, raising `QueryError` if there are none or several."""
    if len(self) != 1:
      raise QueryError(f"expected one call, found {len(self)}")
    return self[0]

  def count(self, *args):
    """The number of calls (or, with an argument, of occurrences of it, as `list.count`)."""
    return list.count(self, *args) if args else len(self)

  def values(self, key):
    """The value of `key` (a function on calls, a parameter name or a position) for each call."""
    k = _key(key)
    return [_holds(k, c, "key") for c in self]

  def group_by(self, key):
    """A dict from each value of `key` (a function on calls, a parameter name or a position) to
    the calls having it, in order of first appearance."""
    k = _key(key)
    groups = {}
    for c in self:
      groups.setdefault(_freeze(_holds(k, c, "key")), Calls()).append(c)
    return groups

  def count_by(self, key):
    """A `collections.Counter` from each value of `key` to its number of calls."""
    k = _key(key)
    return collections.Counter(_freeze(_holds(k, c, "key")) for c in self)

  def functions(self):
    """A dict from each function to its number of calls in the selection, most frequent first."""
    return dict(collections.Counter(c.function for c in self).most_common())

  def show(self, limit=20):
    """Prints the first `limit` calls, one per line."""
    for c in self[:limit]:
      print(c)
    if len(self) > limit:
      print(f"… {len(self) - limit} more")

  def __repr__(self):
    if len(self) <= 5:
      return f"Calls({list.__repr__(self)})"
    return f"<{len(self)} calls: {self[0]!r}, …>"


def _freeze(value):
  """`value`, made hashable (lists become tuples and dicts tuples of pairs)."""
  if isinstance(value, list):
    return tuple(_freeze(x) for x in value)
  if isinstance(value, dict):
    return tuple((k, _freeze(v)) for k, v in value.items())
  return value


class Trace(object):
  """A recorded trace."""

  def __getattr__(self, name):
    _no_attribute(self, name)

  def __init__(self, identifier):
    self.identifier = identifier
    self._calls = Calls()
    self._by_index = {}
    self._by_index_calls = []
    self._snaps = Snaps()
    self._snaps_by_index = {}
    self._functions = {}
    self._selections = {}

  def calls(self, *selectors, **conditions):
    """The calls selected by every selector and satisfying every condition (see the module's
    documentation), in recording order; with no arguments, every call."""
    return self._calls.where(*selectors, **conditions)

  def call(self, index):
    """The call recorded at `index` (as shown by `#index`)."""
    return self._by_index[index]

  def roots(self):
    """The calls made at the top level (or by each thread)."""
    return Calls(c for c in self._calls if c.caller is None)

  def snaps(self, label=None):
    """The snaps with `label` (a string or a compiled regular expression), or all of them."""
    return self._snaps.labeled(label)

  def functions(self):
    """A dict from each recorded function to its number of calls, most frequent first."""
    return dict(sorted(self._functions.items(), key=lambda x: -x[1]))

  def __repr__(self):
    return f"<trace with {len(self._calls)} calls and {len(self._snaps)} snaps>"


def load(path):
  """Loads the trace written by the recorder at `path`."""
  with open(path, "rb") as f:
    data = f.read()
  r = Reader(data)
  if r.bytes(4) != b"pmdb":
    raise ValueError(f"{path} isn't a pmdb trace")
  r.bytes(2)  # the version
  trace = Trace(r.bytes(16).hex())
  n = r.unsigned()
  raw = []
  for _ in range(n):
    tag = r.byte()
    location = (r.string(), r.unsigned())
    if tag == 0x01:
      label = r.string() if r.byte() else None
      raw.append(("snap", location, label, r.value()))
    elif tag == 0x02 or tag == 0x04:
      function = r.string()
      definition = (r.string(), r.unsigned()) if tag == 0x04 else None
      args, names = [], [] if tag == 0x04 else None
      for _ in range(r.unsigned()):
        if tag == 0x04:
          names.append(r.string())
        args.append(r.value())
      kwargs = {}
      for _ in range(r.unsigned()):
        k = r.string()
        kwargs[k] = r.value()
      raw.append(("call", location, function, definition, args, names, kwargs))
    elif tag == 0x03:
      call = r.unsigned()
      raised = bool(r.byte())
      raw.append(("outcome", location, call, raised, r.value()))
    else:
      raise ValueError(f"unknown observation tag {tag:#x}")
  parents = [r.unsigned() for _ in range(n)]

  calls, snaps = [], []
  by_index, depth, last_child = {}, {}, {}
  for i, (o, p) in enumerate(zip(raw, parents)):
    if o[0] == "call":
      d = depth[i] = depth.get(p, 0) + 1 if i != 0 else 0
      c = Call(trace, i, o[1], o[2], o[3], o[4], o[5], o[6], p, d - 1)
      by_index[i] = c
      if i != 0:
        calls.append(c)
        trace._functions[c.function] = trace._functions.get(c.function, 0) + 1
      if p in by_index and i != p:
        by_index[p].children_indices.append(i)
      last_child[p] = ("call", i)
    elif o[0] == "outcome":
      c = by_index.get(o[2])
      if c is not None and c._outcome is None:
        c.finish = i
        value = o[4]
        c._outcome = ("raised", Raised(value) if isinstance(value, dict) else value) if o[3] \
          else ("returned", value)
        c.end_location = o[1]
      last_child[p] = ("outcome", i)
    else:
      label, value = o[2], o[3]
      # In traces of decorated functions, a call's outcome is the snap labeled
      # `<function>.$result` or `.$exception` that immediately follows it among its parent's
      # children.
      previous = last_child.get(p)
      last_child[p] = ("snap", i)
      if previous is not None and previous[0] == "call":
        c = by_index[previous[1]]
        if c._outcome is None and label == c.function + ".$result":
          c._outcome, c.finish = ("returned", value), i
          continue
        if c._outcome is None and label == c.function + ".$exception":
          c._outcome, c.finish = ("raised", Raised(value) if isinstance(value, dict) else value), i
          continue
      s = Snap(trace, i, o[1], label, value, p)
      snaps.append(s)
      trace._snaps_by_index[i] = s
      if p in by_index:
        by_index[p].snap_indices.append(i)
  # A call without a recorded outcome ends with the last observation made during it.
  for i in range(n - 1, 0, -1):
    c = by_index.get(i)
    if c is not None and c._outcome is None and c.children_indices:
      c.finish = max(c.finish, *(by_index[j].finish for j in c.children_indices))
    if c is not None and c._outcome is None and c.snap_indices:
      c.finish = max(c.finish, c.snap_indices[-1])
  trace._calls = Calls(calls)
  trace._by_index = {i: c for i, c in by_index.items() if i != 0}
  trace._by_index_calls = [c.index for c in calls]
  trace._snaps = Snaps(snaps)
  return trace
