import enum
import pickle
import struct
import types

from enum import Enum


class TypeIdentifier(Enum):
  Null      = 0x00
  Integer   = 0x01
  Float     = 0x02
  String    = 0x03
  Array     = 0x04
  Table     = 0x05
  Boolean   = 0x06
  Reference = 0x07
  Function  = 0xfe
  Object    = 0xff


def inline(o):
  """Returns whether `o` is written in place rather than in the table of values: `None`, a
  Boolean, a number, or a string of fewer than 8 characters."""
  return o is None or type(o) in (bool, int, float) or (type(o) is str and len(o) < 8)


class ValueTable(object):
  """The values of a trace that aren't written in place, each stored once and referred to by its
  position.

  Values are compared by their encoding, so equal values are stored once whatever the objects
  that had them.
  """

  def __init__(self):
    self.positions = {}
    self.entries = []

  def intern(self, encoding):
    """Returns the position of the value whose encoding is `encoding`, adding it if needed."""
    i = self.positions.get(encoding)
    if i is None:
      i = self.positions[encoding] = len(self.entries)
      self.entries.append(encoding)
    return i


class Archive(object):
  """A buffer of encoded values. Values other than those written in place (see `inline`) are
  added to `table`, if given, and written as references to it."""

  def __init__(self, table=None):
    self.buffer = bytearray()
    self.table = table

  def write(self, item):
    item.serialize(self)

  def write_byte(self, b):
    self.buffer.append(b)

  def write_bytes(self, bs):
    self.buffer += bs

  def write_unsigned(self, n):
    assert n >= 0
    while True:
      b = n & 0x7f
      n = n >> 7
      if n != 0:
        b = b | 0x80
      self.write_byte(b)
      if n == 0:
        break

  def write_signed(self, n):
    while True:
      b = n & 0x7f
      n = n >> 7
      if (((n == 0) and ((b & 0x40) == 0)) or ((n == -1) and ((b & 0x40) != 0))):
        self.write_byte(b)
        return
      else:
        self.write_byte(b | 0x80)

  def write_string(self, s):
    units = s.encode('utf-8')
    self.write_unsigned(len(units))
    self.write_bytes(units)

  def write_table(self, entries, count, enclosing):
    """Writes the `count` pairs of a string and a value in `entries` as a table."""
    self.write_byte(TypeIdentifier.Table.value)
    self.write_unsigned(count)
    for k, x in entries:
      self.write_string(k)
      self.write_object(x, enclosing)

  def write_object(self, o, enclosing=frozenset()):
    """
    Writes `o`, which is contained in the arrays and tables whose identities are in `enclosing`.
    """
    if self.table is None or inline(o):
      self.write_contents(o, enclosing)
      return
    contents = Archive(self.table)
    contents.write_contents(o, enclosing)
    encoding = bytes(contents.buffer)
    if inline_encoding(encoding):
      # E.g., an object whose conversion is a number.
      self.write_bytes(encoding)
    else:
      self.write_byte(TypeIdentifier.Reference.value)
      self.write_unsigned(self.table.intern(encoding))

  def write_contents(self, o, enclosing):
    """Writes `o` in place, its elements being written with `write_object`."""
    # Handle the absence of a value.
    if o is None:
      self.write_byte(TypeIdentifier.Null.value)

    # Handle Booleans, which are also integers in Python.
    elif isinstance(o, bool):
      self.write_byte(TypeIdentifier.Boolean.value)
      self.write_byte(int(o))

    # Handle integers.
    elif isinstance(o, int):
      self.write_byte(TypeIdentifier.Integer.value)
      self.write_signed(o)

    # Handle floating-point numbers.
    elif isinstance(o, float):
      self.write_byte(TypeIdentifier.Float.value)
      self.write_bytes(struct.pack("<d", o))

    # Handle character strings.
    elif isinstance(o, str):
      self.write_byte(TypeIdentifier.String.value)
      self.write_string(o)

    # Handle named tuples, unless they contain themselves.
    elif isinstance(o, tuple) and hasattr(type(o), "_fields") and id(o) not in enclosing:
      self.write_table(zip(type(o)._fields, o), len(o), enclosing | {id(o)})

    # Handle lists and tuples, unless they contain themselves.
    elif isinstance(o, (list, tuple)) and id(o) not in enclosing:
      self.write_byte(TypeIdentifier.Array.value)
      self.write_unsigned(len(o))
      for x in o:
        self.write_object(x, enclosing | {id(o)})

    # Handle dictionaries with string keys, unless they contain themselves.
    elif isinstance(o, dict) and id(o) not in enclosing and all(isinstance(k, str) for k in o):
      self.write_table(o.items(), len(o), enclosing | {id(o)})

    # Handle functions.
    elif isinstance(o, types.LambdaType):
      self.write_byte(TypeIdentifier.Function.value)
      self.write_string(o.__qualname__)

    # Handle objects whose type defines how they are recorded, unless they contain themselves.
    elif (convert := conversion(type(o))) is not None and id(o) not in enclosing:
      self.write_contents(convert(o), enclosing | {id(o)})

    # Handle enumerations, which are recorded as the names of their members.
    elif isinstance(o, enum.Enum) and isinstance(o.name, str):
      self.write_byte(TypeIdentifier.String.value)
      self.write_string(o.name)

    # Handle arbitrary objects, writing a description of those that cannot be pickled (e.g.,
    # generators, coroutines, or locks) so that they do not prevent the trace from being written.
    else:
      try:
        bs = pickle.dumps(o)
      except Exception:
        self.write_byte(TypeIdentifier.String.value)
        self.write_string(describe(o))
      else:
        self.write_byte(TypeIdentifier.Object.value)
        self.write_unsigned(len(bs))
        self.write_bytes(bs)


def inline_encoding(encoding):
  """Returns whether `encoding` is that of a value written in place (see `inline`)."""
  tag = encoding[0]
  if tag in (0x00, 0x01, 0x02, 0x06):
    return True
  if tag != TypeIdentifier.String.value:
    return False
  n = shift = 0
  i = 1
  while True:
    b = encoding[i]
    n |= (b & 0x7f) << shift
    shift += 7
    i += 1
    if not b & 0x80:
      break
  return len(encoding[i:i + n].decode("utf-8")) < 8


conversions = {}


def register(cls, convert):
  """
  Records the instances of `cls` and its subclasses as the values returned by `convert`.

  This conversion takes precedence over the method `__pmdb__` that a class can define to the same
  effect. It does not apply to the types whose instances are recorded as values of their own,
  i.e., `None`, Booleans, integers, floating-point numbers, strings, lists, tuples, dictionaries with
  string keys, and functions.
  """
  conversions[cls] = convert


def conversion(t):
  """Returns the function converting instances of `t` to the values recording them, if any."""
  for c in t.__mro__:
    if c in conversions:
      return conversions[c]
  return getattr(t, "__pmdb__", None)


def describe(o, convert=repr):
  """Returns `convert(o)`, or a generic description of `o` if `convert` raises."""
  try:
    return convert(o)
  except Exception:
    return f"<{type(o).__qualname__} object>"
