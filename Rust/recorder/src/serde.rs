//! The recording of values whose types implement `serde::Serialize`.
//!
//! Serde's data model is mapped onto the values of a trace using the same conventions as derived
//! implementations of [`Record`], with one exception: unit variants are always recorded as
//! strings because a serializer can't tell whether the other variants of an enum have fields.

use crate::value::{ArrayWriter, Encoder, Record, TableWriter, VARIANT_KEY, ValueWriter};
use serde::ser::{self, Serialize};
use std::fmt;

/// A wrapper recording the value of a type implementing `serde::Serialize`.
pub struct Serde<T>(pub T);

impl<T: Serialize> Record for Serde<T> {
  fn record(&self, w: ValueWriter<'_>) {
    // An error leaves the writers it interrupts, which record `none` for their missing parts.
    let _ = self.0.serialize(Serializer(w));
  }
}

/// Records `value` to `w`, for use in `#[pmdb(with = pmdb_recorder::serde::record)]`.
pub fn record<T: Serialize + ?Sized>(value: &T, w: ValueWriter<'_>) {
  Serde(value).record(w)
}

/// An error reported by an implementation of `serde::Serialize`.
#[derive(Debug)]
pub struct Error(String);

impl fmt::Display for Error {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    f.write_str(&self.0)
  }
}

impl std::error::Error for Error {}

impl ser::Error for Error {
  fn custom<T: fmt::Display>(msg: T) -> Self {
    Error(msg.to_string())
  }
}

/// A serializer writing a value to a trace.
pub struct Serializer<'a>(pub ValueWriter<'a>);

/// Returns the encoding of `value`.
fn encode<T: Serialize + ?Sized>(value: &T) -> Result<Vec<u8>, Error> {
  let mut result = Ok(());
  let bs = Encoder::encode(|w| result = value.serialize(Serializer(w)));
  result.map(|_| bs)
}

impl<'a> ser::Serializer for Serializer<'a> {
  type Ok = ();
  type Error = Error;
  type SerializeSeq = Sequence<'a>;
  type SerializeTuple = ArrayWriter<'a>;
  type SerializeTupleStruct = ArrayWriter<'a>;
  type SerializeTupleVariant = Fields<'a>;
  type SerializeMap = Map<'a>;
  type SerializeStruct = TableWriter<'a>;
  type SerializeStructVariant = TableWriter<'a>;

  fn serialize_bool(self, v: bool) -> Result<(), Error> {
    self.0.bool(v);
    Ok(())
  }

  fn serialize_i8(self, v: i8) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_i16(self, v: i16) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_i32(self, v: i32) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_i64(self, v: i64) -> Result<(), Error> {
    self.0.integer(v);
    Ok(())
  }

  fn serialize_i128(self, v: i128) -> Result<(), Error> {
    self.0.wide_integer(v);
    Ok(())
  }

  fn serialize_u8(self, v: u8) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_u16(self, v: u16) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_u32(self, v: u32) -> Result<(), Error> {
    self.0.integer(v.into());
    Ok(())
  }

  fn serialize_u64(self, v: u64) -> Result<(), Error> {
    self.0.wide_unsigned(v.into());
    Ok(())
  }

  fn serialize_u128(self, v: u128) -> Result<(), Error> {
    self.0.wide_unsigned(v);
    Ok(())
  }

  fn serialize_f32(self, v: f32) -> Result<(), Error> {
    self.0.float(v.into());
    Ok(())
  }

  fn serialize_f64(self, v: f64) -> Result<(), Error> {
    self.0.float(v);
    Ok(())
  }

  fn serialize_char(self, v: char) -> Result<(), Error> {
    self.0.string(v.encode_utf8(&mut [0; 4]));
    Ok(())
  }

  fn serialize_str(self, v: &str) -> Result<(), Error> {
    self.0.string(v);
    Ok(())
  }

  fn serialize_bytes(self, v: &[u8]) -> Result<(), Error> {
    self.0.object(v);
    Ok(())
  }

  fn serialize_none(self) -> Result<(), Error> {
    self.0.null();
    Ok(())
  }

  fn serialize_some<T: Serialize + ?Sized>(self, value: &T) -> Result<(), Error> {
    value.serialize(self)
  }

  fn serialize_unit(self) -> Result<(), Error> {
    self.0.null();
    Ok(())
  }

  fn serialize_unit_struct(self, name: &'static str) -> Result<(), Error> {
    self.0.string(name);
    Ok(())
  }

  fn serialize_unit_variant(
    self, _: &'static str, _: u32, variant: &'static str,
  ) -> Result<(), Error> {
    self.0.string(variant);
    Ok(())
  }

  fn serialize_newtype_struct<T: Serialize + ?Sized>(
    self, _: &'static str, value: &T,
  ) -> Result<(), Error> {
    let mut a = self.0.array(1);
    value.serialize(Serializer(a.element()))
  }

  fn serialize_newtype_variant<T: Serialize + ?Sized>(
    self, _: &'static str, _: u32, variant: &'static str, value: &T,
  ) -> Result<(), Error> {
    let mut t = self.0.table(2);
    t.entry(VARIANT_KEY).string(variant);
    value.serialize(Serializer(t.entry("0")))
  }

  fn serialize_seq(self, len: Option<usize>) -> Result<Sequence<'a>, Error> {
    Ok(match len {
      Some(n) => Sequence::Known(self.0.array(n)),
      None => Sequence::Unknown(self.0, Vec::new()),
    })
  }

  fn serialize_tuple(self, len: usize) -> Result<ArrayWriter<'a>, Error> {
    Ok(self.0.array(len))
  }

  fn serialize_tuple_struct(self, _: &'static str, len: usize) -> Result<ArrayWriter<'a>, Error> {
    Ok(self.0.array(len))
  }

  fn serialize_tuple_variant(
    self, _: &'static str, _: u32, variant: &'static str, len: usize,
  ) -> Result<Fields<'a>, Error> {
    let mut t = self.0.table(len + 1);
    t.entry(VARIANT_KEY).string(variant);
    Ok(Fields { table: t, next: 0 })
  }

  fn serialize_map(self, _: Option<usize>) -> Result<Map<'a>, Error> {
    Ok(Map {
      writer: self.0,
      keys: Vec::new(),
      values: Vec::new(),
    })
  }

  fn serialize_struct(self, _: &'static str, len: usize) -> Result<TableWriter<'a>, Error> {
    Ok(self.0.table(len))
  }

  fn serialize_struct_variant(
    self, _: &'static str, _: u32, variant: &'static str, len: usize,
  ) -> Result<TableWriter<'a>, Error> {
    let mut t = self.0.table(len + 1);
    t.entry(VARIANT_KEY).string(variant);
    Ok(t)
  }
}

/// The serialization of a sequence.
pub enum Sequence<'a> {
  /// A sequence whose length is known up front, whose elements are written as they come.
  Known(ArrayWriter<'a>),

  /// A sequence whose length is unknown, whose elements are buffered.
  Unknown(ValueWriter<'a>, Vec<Vec<u8>>),
}

impl ser::SerializeSeq for Sequence<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_element<T: Serialize + ?Sized>(&mut self, value: &T) -> Result<(), Error> {
    match self {
      Sequence::Known(a) => value.serialize(Serializer(a.element())),
      Sequence::Unknown(_, xs) => {
        xs.push(encode(value)?);
        Ok(())
      }
    }
  }

  fn end(self) -> Result<(), Error> {
    if let Sequence::Unknown(w, xs) = self {
      let mut a = w.array(xs.len());
      for x in &xs {
        a.element().raw(x);
      }
    }
    Ok(())
  }
}

impl ser::SerializeTuple for ArrayWriter<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_element<T: Serialize + ?Sized>(&mut self, value: &T) -> Result<(), Error> {
    value.serialize(Serializer(self.element()))
  }

  fn end(self) -> Result<(), Error> {
    Ok(())
  }
}

impl ser::SerializeTupleStruct for ArrayWriter<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_field<T: Serialize + ?Sized>(&mut self, value: &T) -> Result<(), Error> {
    value.serialize(Serializer(self.element()))
  }

  fn end(self) -> Result<(), Error> {
    Ok(())
  }
}

/// The serialization of the fields of a tuple variant, which are keyed by their position.
pub struct Fields<'a> {
  table: TableWriter<'a>,
  next: usize,
}

impl ser::SerializeTupleVariant for Fields<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_field<T: Serialize + ?Sized>(&mut self, value: &T) -> Result<(), Error> {
    let key = self.next.to_string();
    self.next += 1;
    value.serialize(Serializer(self.table.entry(&key)))
  }

  fn end(self) -> Result<(), Error> {
    Ok(())
  }
}

/// The serialization of a map, which is buffered until all keys are known to tell whether it can
/// be recorded as a table.
pub struct Map<'a> {
  writer: ValueWriter<'a>,
  keys: Vec<Vec<u8>>,
  values: Vec<Vec<u8>>,
}

impl ser::SerializeMap for Map<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_key<T: Serialize + ?Sized>(&mut self, key: &T) -> Result<(), Error> {
    self.keys.push(encode(key)?);
    Ok(())
  }

  fn serialize_value<T: Serialize + ?Sized>(&mut self, value: &T) -> Result<(), Error> {
    self.values.push(encode(value)?);
    Ok(())
  }

  fn end(self) -> Result<(), Error> {
    let values = self.values;
    self.writer.keyed(&self.keys, |i, w| w.raw(&values[i]));
    Ok(())
  }
}

impl ser::SerializeStruct for TableWriter<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_field<T: Serialize + ?Sized>(
    &mut self, key: &'static str, value: &T,
  ) -> Result<(), Error> {
    value.serialize(Serializer(self.entry(key)))
  }

  fn end(self) -> Result<(), Error> {
    Ok(())
  }
}

impl ser::SerializeStructVariant for TableWriter<'_> {
  type Ok = ();
  type Error = Error;

  fn serialize_field<T: Serialize + ?Sized>(
    &mut self, key: &'static str, value: &T,
  ) -> Result<(), Error> {
    value.serialize(Serializer(self.entry(key)))
  }

  fn end(self) -> Result<(), Error> {
    Ok(())
  }
}
