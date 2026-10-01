//! The encoding of Rust values as the values of a trace.

use crate::archive::{write_signed, write_string, write_unsigned};
use std::borrow::Cow;
use std::cell::{Cell, RefCell};
use std::collections::{BTreeMap, BTreeSet, BinaryHeap, HashMap, HashSet, LinkedList, VecDeque};
use std::hash::BuildHasher;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::sync::{Arc, Mutex, RwLock};

/// A tag identifying the type of a value in a trace.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Tag {
  Null = 0x00,
  Integer = 0x01,
  Float = 0x02,
  String = 0x03,
  Array = 0x04,
  Table = 0x05,
  Boolean = 0x06,
  Function = 0xfe,
  Object = 0xff,
}

/// The key under which the tables representing enum variants store the name of their variant.
pub const VARIANT_KEY: &str = "$variant";

/// A type whose values can be recorded in a trace.
///
/// This trait is usually derived (see [`macro@crate::Record`]), which records structs with named
/// fields as tables, other structs as arrays, and enums as
/// the name of their variant if none of their variants has fields, or as tables otherwise.
///
/// Implementations write exactly one value to the writer they are given. A writer that is dropped
/// without having been written records `none`.
pub trait Record {
  /// Writes the value of `self` to `w`.
  fn record(&self, w: ValueWriter<'_>);
}

/// The state of the encoding of a value.
#[derive(Default)]
pub(crate) struct Encoder {
  /// The bytes written so far.
  pub(crate) out: Vec<u8>,

  /// The addresses of the shared values whose contents are being written, outermost first.
  enclosing: Vec<*const ()>,
}

impl Encoder {
  /// Returns the encoding of `value`, which is written by `write`.
  pub(crate) fn encode(write: impl FnOnce(ValueWriter<'_>)) -> Vec<u8> {
    let mut e = Encoder::default();
    write(ValueWriter::new(&mut e));
    e.out
  }
}

/// A sink accepting exactly one value.
pub struct ValueWriter<'a> {
  /// The state of the encoding.
  encoder: &'a mut Encoder,

  /// `true` iff a value has been written.
  done: bool,
}

impl<'a> ValueWriter<'a> {
  fn new(encoder: &'a mut Encoder) -> Self {
    Self {
      encoder,
      done: false,
    }
  }

  /// Writes `tag` and returns the output stream of `self`, marking `self` as written.
  fn begin(&mut self, tag: Tag) -> &mut Vec<u8> {
    self.done = true;
    self.encoder.out.push(tag as u8);
    &mut self.encoder.out
  }

  /// Records the absence of a value.
  pub fn null(mut self) {
    self.begin(Tag::Null);
  }

  /// Records `b`.
  pub fn bool(mut self, b: bool) {
    self.begin(Tag::Boolean).push(b as u8);
  }

  /// Records `n`.
  pub fn integer(mut self, n: i64) {
    write_signed(self.begin(Tag::Integer), n);
  }

  /// Records `n` as an integer if it is representable as an `i64`, or otherwise as an object
  /// containing its 16 bytes in little-endian order.
  pub fn wide_integer(self, n: i128) {
    match i64::try_from(n) {
      Ok(m) => self.integer(m),
      Err(_) => self.object(&n.to_le_bytes()),
    }
  }

  /// Records `n` as an integer if it is representable as an `i64`, or otherwise as an object
  /// containing its 16 bytes in little-endian order.
  pub fn wide_unsigned(self, n: u128) {
    match i64::try_from(n) {
      Ok(m) => self.integer(m),
      Err(_) => self.object(&n.to_le_bytes()),
    }
  }

  /// Records `n`.
  pub fn float(mut self, n: f64) {
    self.begin(Tag::Float).extend_from_slice(&n.to_le_bytes());
  }

  /// Records `s`.
  pub fn string(mut self, s: &str) {
    write_string(self.begin(Tag::String), s);
  }

  /// Records a function named `name`.
  pub fn function(mut self, name: &str) {
    write_string(self.begin(Tag::Function), name);
  }

  /// Records an object whose contents are the bytes `bs`.
  pub fn object(mut self, bs: &[u8]) {
    let out = self.begin(Tag::Object);
    write_unsigned(out, bs.len() as u64);
    out.extend_from_slice(bs);
  }

  /// Records an array of `count` elements, which are then written by the returned writer.
  pub fn array(mut self, count: usize) -> ArrayWriter<'a> {
    write_unsigned(self.begin(Tag::Array), count as u64);
    ArrayWriter {
      encoder: self.take(),
      remaining: count,
    }
  }

  /// Records a table of `count` entries, which are then written by the returned writer.
  ///
  /// The keys of the entries must be distinct, or the trace will be rejected by `pmdb`.
  pub fn table(mut self, count: usize) -> TableWriter<'a> {
    write_unsigned(self.begin(Tag::Table), count as u64);
    TableWriter {
      encoder: self.take(),
      remaining: count,
    }
  }

  /// Records the elements of `items` as an array.
  pub fn elements<'i, T: Record + ?Sized + 'i>(
    self, items: impl IntoIterator<Item = &'i T, IntoIter: ExactSizeIterator>,
  ) {
    let items = items.into_iter();
    let mut a = self.array(items.len());
    for x in items {
      x.record(a.element());
    }
  }

  /// Records the entries of `items` as a table if all keys are recorded as distinct strings, or
  /// as an array of key-value pairs otherwise.
  pub fn entries<'i, K: Record + ?Sized + 'i, V: Record + ?Sized + 'i>(
    self, items: impl IntoIterator<Item = (&'i K, &'i V), IntoIter: ExactSizeIterator>,
  ) {
    // Encode the keys first to determine whether they can be the keys of a table.
    let items = items.into_iter();
    let mut keys = Vec::with_capacity(items.len());
    let mut values = Vec::with_capacity(items.len());
    for (k, v) in items {
      keys.push(self.encoder.scratch(|w| k.record(w)));
      values.push(v);
    }
    self.keyed(&keys, |i, w| values[i].record(w))
  }

  /// Records a table whose keys are the strings encoded in `keys` and whose values are written by
  /// `value`, which is called with the position of each entry, if all keys are distinct strings,
  /// or an array of key-value pairs otherwise.
  pub(crate) fn keyed(self, keys: &[Vec<u8>], mut value: impl FnMut(usize, ValueWriter<'_>)) {
    let mut seen = HashSet::with_capacity(keys.len());
    let is_table = keys
      .iter()
      .all(|k| k.first() == Some(&(Tag::String as u8)) && seen.insert(k));

    if is_table {
      // A string value is its tag followed by its contents, which are encoded like a table key.
      let mut t = self.table(keys.len());
      for (i, k) in keys.iter().enumerate() {
        t.encoder.out.extend_from_slice(&k[1..]);
        t.remaining -= 1;
        value(i, ValueWriter::new(t.encoder));
      }
    } else {
      let mut a = self.array(keys.len());
      for (i, k) in keys.iter().enumerate() {
        let mut pair = a.element().array(2);
        pair.element().raw(k);
        value(i, pair.element());
      }
    }
  }

  /// Records `value`, which is stored at `address`, unless `self` is part of the contents of
  /// `value`, in which case a description of the cycle is recorded.
  ///
  /// This method guards against the infinite recursion that would otherwise result from the
  /// recording of reference cycles (e.g., built with `Rc` and `RefCell`).
  pub fn shared<T: Record + ?Sized>(self, address: *const (), value: &T) {
    if self.encoder.enclosing.contains(&address) {
      self.string("<cycle>");
    } else {
      let e = self.take();
      e.enclosing.push(address);
      value.record(ValueWriter::new(e));
      e.enclosing.pop();
    }
  }

  /// Records `value`.
  pub fn record<T: Record + ?Sized>(self, value: &T) {
    value.record(self)
  }

  /// Writes `bs`, which is the encoding of a value.
  pub(crate) fn raw(mut self, bs: &[u8]) {
    self.done = true;
    self.encoder.out.extend_from_slice(bs);
  }

  /// Marks `self` as written and returns its encoder.
  fn take(mut self) -> &'a mut Encoder {
    self.done = true;
    // `self` has no other field with a destructor, so it can be forgotten after being unpacked.
    let e = unsafe { std::ptr::read(&self.encoder) };
    std::mem::forget(self);
    e
  }
}

impl Drop for ValueWriter<'_> {
  fn drop(&mut self) {
    if !self.done {
      self.encoder.out.push(Tag::Null as u8);
    }
  }
}

impl Encoder {
  /// Returns the encoding of the value written by `write`, without writing it to `self`.
  fn scratch(&mut self, write: impl FnOnce(ValueWriter<'_>)) -> Vec<u8> {
    let saved = std::mem::take(&mut self.out);
    write(ValueWriter::new(self));
    std::mem::replace(&mut self.out, saved)
  }
}

/// A sink accepting the elements of an array.
///
/// Elements that have been announced but not written are recorded as `none` when the writer is
/// dropped.
pub struct ArrayWriter<'a> {
  encoder: &'a mut Encoder,
  remaining: usize,
}

impl ArrayWriter<'_> {
  /// Returns a writer for the next element.
  ///
  /// # Panics
  ///
  /// Panics if all elements announced by [`ValueWriter::array`] have been written.
  pub fn element(&mut self) -> ValueWriter<'_> {
    assert!(self.remaining > 0, "more elements written than announced");
    self.remaining -= 1;
    ValueWriter::new(self.encoder)
  }
}

impl Drop for ArrayWriter<'_> {
  fn drop(&mut self) {
    for _ in 0..self.remaining {
      self.encoder.out.push(Tag::Null as u8);
    }
  }
}

/// A sink accepting the entries of a table.
///
/// Entries that have been announced but not written are recorded with keys made of a dollar sign
/// followed by their position and `none` values when the writer is dropped.
pub struct TableWriter<'a> {
  encoder: &'a mut Encoder,
  remaining: usize,
}

impl TableWriter<'_> {
  /// Returns a writer for the value of the next entry, whose key is `key`.
  ///
  /// # Panics
  ///
  /// Panics if all entries announced by [`ValueWriter::table`] have been written.
  pub fn entry(&mut self, key: &str) -> ValueWriter<'_> {
    assert!(self.remaining > 0, "more entries written than announced");
    self.remaining -= 1;
    write_string(&mut self.encoder.out, key);
    ValueWriter::new(self.encoder)
  }
}

impl Drop for TableWriter<'_> {
  fn drop(&mut self) {
    for i in 0..self.remaining {
      write_string(&mut self.encoder.out, &format!("$missing{i}"));
      self.encoder.out.push(Tag::Null as u8);
    }
  }
}

// --- Implementations for standard types -----------------------------------------------------------

macro_rules! record_integers {
  ($($t:ty),*) => {$(
    impl Record for $t {
      fn record(&self, w: ValueWriter<'_>) { w.integer(*self as i64) }
    }
  )*};
}
record_integers!(i8, i16, i32, i64, u8, u16, u32);

macro_rules! record_wide_integers {
  ($($t:ty => $method:ident as $wide:ty),*) => {$(
    impl Record for $t {
      fn record(&self, w: ValueWriter<'_>) { w.$method(*self as $wide) }
    }
  )*};
}
record_wide_integers!(
  isize => wide_integer as i128, i128 => wide_integer as i128,
  usize => wide_unsigned as u128, u64 => wide_unsigned as u128, u128 => wide_unsigned as u128);

impl Record for bool {
  fn record(&self, w: ValueWriter<'_>) {
    w.bool(*self)
  }
}

impl Record for f32 {
  fn record(&self, w: ValueWriter<'_>) {
    w.float(*self as f64)
  }
}

impl Record for f64 {
  fn record(&self, w: ValueWriter<'_>) {
    w.float(*self)
  }
}

impl Record for char {
  fn record(&self, w: ValueWriter<'_>) {
    w.string(self.encode_utf8(&mut [0; 4]))
  }
}

impl Record for str {
  fn record(&self, w: ValueWriter<'_>) {
    w.string(self)
  }
}

impl Record for String {
  fn record(&self, w: ValueWriter<'_>) {
    w.string(self)
  }
}

impl Record for Path {
  fn record(&self, w: ValueWriter<'_>) {
    w.string(&self.to_string_lossy())
  }
}

impl Record for PathBuf {
  fn record(&self, w: ValueWriter<'_>) {
    w.string(&self.to_string_lossy())
  }
}

impl Record for () {
  fn record(&self, w: ValueWriter<'_>) {
    w.null()
  }
}

impl<T: Record> Record for Option<T> {
  fn record(&self, w: ValueWriter<'_>) {
    match self {
      Some(x) => x.record(w),
      None => w.null(),
    }
  }
}

impl<T: Record, E: Record> Record for Result<T, E> {
  fn record(&self, w: ValueWriter<'_>) {
    let mut t = w.table(2);
    match self {
      Ok(x) => {
        t.entry(VARIANT_KEY).string("Ok");
        x.record(t.entry("0"));
      }
      Err(x) => {
        t.entry(VARIANT_KEY).string("Err");
        x.record(t.entry("0"));
      }
    }
  }
}

impl<T: Record + ?Sized> Record for &T {
  fn record(&self, w: ValueWriter<'_>) {
    (**self).record(w)
  }
}

impl<T: Record + ?Sized> Record for &mut T {
  fn record(&self, w: ValueWriter<'_>) {
    (**self).record(w)
  }
}

impl<T: Record + ?Sized> Record for Box<T> {
  fn record(&self, w: ValueWriter<'_>) {
    (**self).record(w)
  }
}

impl<T: Record + ?Sized> Record for Rc<T> {
  fn record(&self, w: ValueWriter<'_>) {
    w.shared(Rc::as_ptr(self) as *const (), &**self)
  }
}

impl<T: Record + ?Sized> Record for Arc<T> {
  fn record(&self, w: ValueWriter<'_>) {
    w.shared(Arc::as_ptr(self) as *const (), &**self)
  }
}

impl<T: Record + ToOwned + ?Sized> Record for Cow<'_, T> {
  fn record(&self, w: ValueWriter<'_>) {
    (**self).record(w)
  }
}

impl<T: Record + Copy> Record for Cell<T> {
  fn record(&self, w: ValueWriter<'_>) {
    self.get().record(w)
  }
}

impl<T: Record + ?Sized> Record for RefCell<T> {
  fn record(&self, w: ValueWriter<'_>) {
    match self.try_borrow() {
      Ok(x) => x.record(w),
      Err(_) => w.string("<borrowed>"),
    }
  }
}

impl<T: Record + ?Sized> Record for Mutex<T> {
  fn record(&self, w: ValueWriter<'_>) {
    match self.try_lock() {
      Ok(x) => x.record(w),
      Err(_) => w.string("<locked>"),
    }
  }
}

impl<T: Record + ?Sized> Record for RwLock<T> {
  fn record(&self, w: ValueWriter<'_>) {
    match self.try_read() {
      Ok(x) => x.record(w),
      Err(_) => w.string("<locked>"),
    }
  }
}

impl<T: Record> Record for [T] {
  fn record(&self, w: ValueWriter<'_>) {
    w.elements(self)
  }
}

impl<T: Record, const N: usize> Record for [T; N] {
  fn record(&self, w: ValueWriter<'_>) {
    w.elements(self)
  }
}

macro_rules! record_sequences {
  ($($t:ident $(: $bound:path)?),*) => {$(
    impl<T: Record $(+ $bound)?> Record for $t<T> {
      fn record(&self, w: ValueWriter<'_>) { w.elements(self) }
    }
  )*};
}
record_sequences!(Vec, VecDeque, LinkedList, BTreeSet, BinaryHeap);

impl<T: Record, S: BuildHasher> Record for HashSet<T, S> {
  fn record(&self, w: ValueWriter<'_>) {
    w.elements(self)
  }
}

impl<K: Record, V: Record, S: BuildHasher> Record for HashMap<K, V, S> {
  fn record(&self, w: ValueWriter<'_>) {
    w.entries(self)
  }
}

impl<K: Record, V: Record> Record for BTreeMap<K, V> {
  fn record(&self, w: ValueWriter<'_>) {
    w.entries(self)
  }
}

macro_rules! record_tuples {
  ($(($($t:ident $i:tt),+)),*) => {$(
    impl<$($t: Record),+> Record for ($($t,)+) {
      fn record(&self, w: ValueWriter<'_>) {
        let mut a = w.array([$($i),+].len());
        $(self.$i.record(a.element());)+
      }
    }
  )*};
}
record_tuples!(
  (A 0),
  (A 0, B 1),
  (A 0, B 1, C 2),
  (A 0, B 1, C 2, D 3),
  (A 0, B 1, C 2, D 3, E 4),
  (A 0, B 1, C 2, D 3, E 4, F 5),
  (A 0, B 1, C 2, D 3, E 4, F 5, G 6),
  (A 0, B 1, C 2, D 3, E 4, F 5, G 6, H 7));
