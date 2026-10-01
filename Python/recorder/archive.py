import pickle
import struct
import types

from enum import Enum


class TypeIdentifier(Enum):
  Integer   = 0x01
  Float     = 0x02
  String    = 0x03
  Array     = 0x04
  Table     = 0x05
  Function  = 0xfe
  Object    = 0xff


class Archive(object):

  def __init__(self):
    self.buffer = bytearray()

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

  def write_object(self, o, enclosing=frozenset()):
    """
    Writes `o`, which is contained in the arrays and tables whose identities are in `enclosing`.
    """
    # Handle signed integers whose two's complement representation requires at most 64 bits.
    if isinstance(o, int) and -(1 << 63) <= o < (1 << 63):
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

    # Handle lists and tuples, unless they contain themselves.
    elif isinstance(o, (list, tuple)) and id(o) not in enclosing:
      self.write_byte(TypeIdentifier.Array.value)
      self.write_unsigned(len(o))
      for x in o:
        self.write_object(x, enclosing | {id(o)})

    # Handle dictionaries with string keys, unless they contain themselves.
    elif isinstance(o, dict) and id(o) not in enclosing and all(isinstance(k, str) for k in o):
      self.write_byte(TypeIdentifier.Table.value)
      self.write_unsigned(len(o))
      for k, x in o.items():
        self.write_string(k)
        self.write_object(x, enclosing | {id(o)})

    # Handle functions.
    elif isinstance(o, types.LambdaType):
      self.write_byte(TypeIdentifier.Function.value)
      self.write_string(o.__qualname__)

    # Handle arbitrary objects.
    else:
      self.write_byte(TypeIdentifier.Object.value)
      bs = pickle.dumps(o)
      self.write_unsigned(len(bs))
      self.write_bytes(bs)
