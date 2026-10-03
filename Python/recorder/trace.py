"""Reading traces written by the recorder, and querying them in Python.

    import recorder
    t = recorder.load("trace.pmdb")
    bad = t.calls("ship").raised("AssertionError").first()
    ok = t.calls("ship").returned()
    bad.args, bad.location, bad.path()
    t.calls("deposit").before(bad).where(lambda c: c.args[0]["id"] == bad.args[0]["id"])
    collections.Counter(c.args[0]["region"] for c in ok)

A trace is a tree of observations in recording order: calls, each followed by its outcome, and
snaps. `Trace.calls` is every call in that order (the recorder's root excluded); selections are
lists of calls with chainable filters. Values are Python values: `None`, Booleans, integers,
floats, strings, lists (arrays) and dicts (tables), plus `Function` for functions and `Opaque`
for objects the recorder pickled or described.
"""

import pickle
import re
import struct


class Opaque(object):
  """An object the recorder couldn't record as a value: its pickle, or a description of it."""

  __slots__ = ("pickled", "description")

  def __init__(self, pickled=None, description=None):
    self.pickled = pickled
    self.description = description

  def unpickle(self):
    """Returns the object, unpickled; this runs code of the program's modules, which must be
    importable (and trusted)."""
    if self.pickled is None:
      raise ValueError(f"no pickle recorded for {self.description}")
    return pickle.loads(self.pickled)

  def __repr__(self):
    return self.description if self.description is not None else "<object>"

  def __eq__(self, other):
    return isinstance(other, Opaque) and (self.pickled, self.description) == (
      other.pickled, other.description)

  def __hash__(self):
    return hash((self.pickled, self.description))


class Function(str):
  """A function, recorded by its qualified name."""

  def __repr__(self):
    return f"<function {str(self)}>"


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


class Raised(dict):
  """The exception a call raised: a dict with its `type` and `message`."""

  @property
  def type(self):
    return self.get("type")

  @property
  def message(self):
    return self.get("message")


class Call(object):
  """A recorded call: its function, arguments as they were when it started, outcome and place in
  the tree of calls."""

  __slots__ = ("trace", "index", "location", "function", "args", "kwargs", "parent_index",
               "children_indices", "end", "_outcome", "depth")

  def __init__(self, trace, index, location, function, args, kwargs, parent_index, depth):
    self.trace = trace
    self.index = index            # position in recording order (of all observations)
    self.location = location      # (file, line) of the call site
    self.function = function
    self.args = args              # positional arguments (methods have `self` first)
    self.kwargs = kwargs          # named arguments
    self.parent_index = parent_index
    self.children_indices = []
    self.end = index              # index of the last observation in this call's subtree
    self._outcome = None          # ("returned", value) or ("raised", Raised)
    self.depth = depth

  @property
  def returned(self):
    """`True` iff the call's return was recorded."""
    return self._outcome is not None and self._outcome[0] == "returned"

  @property
  def result(self):
    """The value the call returned, or `None` if it didn't return (see `returned`)."""
    return self._outcome[1] if self.returned else None

  @property
  def exception(self):
    """The exception the call raised (a `Raised` dict with `type` and `message`), or `None`."""
    return self._outcome[1] if self._outcome is not None and self._outcome[0] == "raised" else None

  def arg(self, key):
    """The positional argument at `key` if it's an integer, or the named argument `key`."""
    return self.args[key] if isinstance(key, int) else self.kwargs[key]

  @property
  def parent(self):
    """The call in which this call was made, or `None` for calls made at the top level."""
    if self.parent_index == 0 or self.parent_index == self.index:  # the recorder's root
      return None
    return self.trace._calls_by_index.get(self.parent_index)

  @property
  def children(self):
    """The calls made directly during this call."""
    return Calls(self.trace._calls_by_index[i] for i in self.children_indices)

  def ancestors(self):
    """The calls enclosing this one, innermost first."""
    result, c = [], self.parent
    while c is not None:
      result.append(c)
      c = c.parent
    return Calls(result)

  def descendants(self):
    """Every call made during this call, directly or not, in recording order."""
    return self.trace.calls().within(self)

  def path(self):
    """The calls from the outermost one to this one."""
    return Calls(list(reversed(self.ancestors())) + [self])

  def __repr__(self):
    args = [repr(a) for a in self.args] + [f"{k}={v!r}" for k, v in self.kwargs.items()]
    text = f"{self.function}({', '.join(args)})"
    if len(text) > 200:
      text = text[:150] + " … " + text[-45:]
    if self.returned:
      text += f" -> {self.result!r}"[:120]
    elif self.exception is not None:
      text += f" raised {self.exception.get('type')}: {self.exception.get('message')}"[:120]
    return f"{self.location[0]}:{self.location[1]}: {text}"


class Snap(object):
  """A recorded value with a label."""

  __slots__ = ("index", "location", "label", "value", "parent_index")

  def __init__(self, index, location, label, value, parent_index):
    self.index, self.location, self.label = index, location, label
    self.value, self.parent_index = value, parent_index

  def __repr__(self):
    return f"{self.location[0]}:{self.location[1]}: {self.label} = {self.value!r}"


def _matcher(name):
  """Returns a predicate on function names for `name`: a string (the exact name, or the last
  component of a qualified one), a compiled regex (matching the whole name), or a predicate."""
  if name is None:
    return lambda f: True
  if isinstance(name, str):
    suffix = "." + name
    return lambda f: f == name or f.endswith(suffix)
  if isinstance(name, re.Pattern):
    return lambda f: name.fullmatch(f) is not None
  return name


class Calls(list):
  """A selection of calls, in recording order, with chainable filters."""

  def named(self, name):
    """The calls of `name` (see `Trace.calls`)."""
    match = _matcher(name)
    return Calls(c for c in self if match(c.function))

  def where(self, predicate):
    """The calls satisfying `predicate`; calls on which it raises are left out."""
    def keep(c):
      try:
        return predicate(c)
      except Exception:
        return False
    return Calls(c for c in self if keep(c))

  def returned(self, predicate=None):
    """The calls that returned (a value satisfying `predicate`, if given)."""
    return Calls(c for c in self if c.returned and (predicate is None or predicate(c.result)))

  def raised(self, type=None):
    """The calls that raised (an exception whose type name is `type`, if given). An exception is
    recorded for every recorded call it passes through."""
    return Calls(c for c in self if c.exception is not None
                 and (type is None or c.exception.get("type") == type))

  def within(self, call):
    """The calls made during `call`, directly or not."""
    return Calls(c for c in self if call.index < c.index <= call.end)

  def before(self, call):
    """The calls that started before `call`."""
    return Calls(c for c in self if c.index < call.index)

  def after(self, call):
    """The calls that started after `call` ended."""
    return Calls(c for c in self if c.index > call.end)

  def first(self):
    return self[0] if self else None

  def last(self):
    return self[-1] if self else None

  def count(self, *args):
    """The number of calls (or, with an argument, of occurrences of it, as `list.count`)."""
    return list.count(self, *args) if args else len(self)

  def group_by(self, key):
    """A dict from each value of `key(call)` to the calls having it, in order of first appearance."""
    groups = {}
    for c in self:
      groups.setdefault(key(c), Calls()).append(c)
    return groups

  def functions(self):
    """A dict from each function name to its number of calls in the selection."""
    counts = {}
    for c in self:
      counts[c.function] = counts.get(c.function, 0) + 1
    return counts

  def show(self, limit=20):
    """Prints the first `limit` calls, one per line."""
    for c in self[:limit]:
      print(c)
    if len(self) > limit:
      print(f"… {len(self) - limit} more")


class Trace(object):
  """A recorded trace."""

  def __init__(self, identifier, call_list, snaps):
    self.identifier = identifier
    self._calls = Calls(call_list)
    self._calls_by_index = {c.index: c for c in call_list}
    self.snaps = snaps

  def calls(self, name=None):
    """The recorded calls, in recording order, optionally only those of `name`: an exact name or
    the last component of a qualified one (`"take"` matches `Parser.take`), a compiled regex
    matching the whole name, or a predicate on names."""
    return self._calls.named(name) if name is not None else Calls(self._calls)

  def functions(self):
    """A dict from each recorded function to its number of calls."""
    return self._calls.functions()

  def __repr__(self):
    return f"<trace {self.identifier} with {len(self._calls)} calls and {len(self.snaps)} snaps>"


def load(path):
  """Loads the trace written by the recorder at `path`."""
  with open(path, "rb") as f:
    data = f.read()
  r = Reader(data)
  if r.bytes(4) != b"pmdb":
    raise ValueError(f"{path} isn't a pmdb trace")
  r.bytes(2)  # the version
  identifier = r.bytes(16).hex()
  n = r.unsigned()
  raw = []
  for _ in range(n):
    tag = r.byte()
    location = (r.string(), r.unsigned())
    if tag == 0x01:
      label = r.string() if r.byte() else None
      raw.append(("snap", location, label, r.value()))
    elif tag == 0x02:
      function = r.string()
      args = [r.value() for _ in range(r.unsigned())]
      kwargs = {}
      for _ in range(r.unsigned()):
        k = r.string()
        kwargs[k] = r.value()
      raw.append(("call", location, function, args, kwargs))
    else:
      raise ValueError(f"unknown observation tag {tag:#x}")
  parents = [r.unsigned() for _ in range(n)]

  trace = Trace(identifier, [], [])
  calls, snaps, depth = [], [], {0: 0}
  by_index = {}
  last_child = {}
  for i, (o, p) in enumerate(zip(raw, parents)):
    if o[0] == "call":
      depth[i] = depth.get(p, 0) + 1
      c = Call(trace, i, o[1], o[2], o[3], o[4], p, depth[i] - 1)
      by_index[i] = c
      if i != 0:
        calls.append(c)
      if p in by_index and i != p:
        by_index[p].children_indices.append(i)
      last_child[p] = ("call", i)
    else:
      s = Snap(i, o[1], o[2], o[3], p)
      # A call's outcome is the snap labeled `<function>.$result` or `.$exception` that
      # immediately follows it among its parent's children.
      previous = last_child.get(p)
      if previous is not None and previous[0] == "call":
        c = by_index[previous[1]]
        if c._outcome is None and o[2] == c.function + ".$result":
          c._outcome = ("returned", o[3])
          last_child[p] = ("snap", i)
          continue
        if c._outcome is None and o[2] == c.function + ".$exception":
          c._outcome = ("raised", Raised(o[3]) if isinstance(o[3], dict) else o[3])
          last_child[p] = ("snap", i)
          continue
      snaps.append(s)
      last_child[p] = ("snap", i)
  # Each call's subtree ends at the last observation whose chain of parents reaches it.
  for i in range(n - 1, 0, -1):
    p = parents[i]
    end = by_index[i].end if i in by_index else i
    if p in by_index and by_index[p].end < end:
      by_index[p].end = end
  trace._calls = Calls(calls)
  trace._calls_by_index = by_index
  trace.snaps = snaps
  return trace
