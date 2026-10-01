import pickle
import struct
import types

from enum import Enum


class TypeIdentifier(Enum):
  Integer   = 0x01
  Float     = 0x02
  String    = 0x03
  Function  = 0xfe
  Object    = 0xff


class Archive(object):

  def __init__(self):
    self.buffer = bytearray()

  def write(self, item):
    item.serialize(self)

  def write_byte(self, b):
    self.buffer.append(b)

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
    units = bytearray(s, 'utf-8')
    self.write_unsigned(len(units))
    for u in units:
      self.write_byte(u)

  def write_object(self, o):
    # Handle signed integers whose two's complement representation requires at most 64 bits.
    if isinstance(o, int) and -(1 << 63) <= o < (1 << 63):
      self.write_byte(TypeIdentifier.Integer.value)
      self.write_signed(o)

    # Handle floating-point numbers.
    elif isinstance(o, float):
      self.write_byte(TypeIdentifier.Float.value)
      for b in bytearray(struct.pack("<d", o)):
        self.write_byte(b)

    # Handle character strings.
    elif isinstance(o, str):
      self.write_byte(TypeIdentifier.String.value)
      self.write_string(o)

    # Handle functions strings.
    elif isinstance(o, types.LambdaType):
      self.write_byte(TypeIdentifier.Function.value)
      self.write_string(o.__qualname__)

    # Handle arbitrary objects.
    else:
      self.write_byte(TypeIdentifier.Object.value)
      bs = pickle.dumps(o)
      self.write_unsigned(len(bs))
      for b in bs:
        self.write_byte(b)
