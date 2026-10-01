mod common;

use common::{Value, decode_value};
use pmdb_recorder::{Record, ValueWriter};
use std::cell::RefCell;
use std::collections::{BTreeMap, HashMap};
use std::rc::Rc;

/// Returns the value recorded for `x`, choosing an encoding like the macros of the recorder do.
macro_rules! recorded {
  ($x:expr) => {{
    #[allow(unused_imports)]
    use pmdb_recorder::__private::probe::*;
    decode_value(&pmdb_recorder::__private::encode(|w| {
      (&Probe(&$x)).__pmdb_record(w)
    }))
  }};
}

#[test]
fn records_scalars() {
  assert_eq!(recorded!(()), Value::Null);
  assert_eq!(recorded!(None::<i32>), Value::Null);
  assert_eq!(recorded!(Some(3u8)), Value::Integer(3));
  assert_eq!(recorded!(true), Value::Integer(1));
  assert_eq!(recorded!(-7i8), Value::Integer(-7));
  assert_eq!(recorded!(i64::MIN), Value::Integer(i64::MIN));
  assert_eq!(recorded!(i64::MAX as u64), Value::Integer(i64::MAX));
  assert_eq!(recorded!(1.5f32), Value::Float(1.5));
  assert_eq!(recorded!('é'), Value::str("é"));
  assert_eq!(recorded!("hi"), Value::str("hi"));
  assert_eq!(recorded!(String::from("hi")), Value::str("hi"));
  assert_eq!(
    recorded!(std::path::PathBuf::from("/a/b")),
    Value::str("/a/b")
  );
}

#[test]
fn records_integers_out_of_range_as_objects() {
  assert_eq!(
    recorded!(u64::MAX),
    Value::Object(u128::from(u64::MAX).to_le_bytes().to_vec())
  );
  assert_eq!(
    recorded!(i128::MIN),
    Value::Object(i128::MIN.to_le_bytes().to_vec())
  );
  assert_eq!(recorded!(5u128), Value::Integer(5));
}

#[test]
fn records_collections() {
  use Value::Integer as I;
  assert_eq!(recorded!(vec![1, 2]), Value::Array(vec![I(1), I(2)]));
  assert_eq!(recorded!([1, 2][..]), Value::Array(vec![I(1), I(2)]));
  assert_eq!(
    recorded!((1, "a")),
    Value::Array(vec![I(1), Value::str("a")])
  );
  assert_eq!(
    recorded!(Box::new([[1]])),
    Value::Array(vec![Value::Array(vec![I(1)])])
  );

  let m = HashMap::from([("a".to_string(), 1), ("b".to_string(), 2)]);
  assert_eq!(recorded!(m), Value::table([("a", I(1)), ("b", I(2))]));

  // Maps whose keys aren't strings are recorded as arrays of pairs.
  let m = BTreeMap::from([(1, "a"), (2, "b")]);
  assert_eq!(
    recorded!(m),
    Value::Array(vec![
      Value::Array(vec![I(1), Value::str("a")]),
      Value::Array(vec![I(2), Value::str("b")]),
    ])
  );
}

#[test]
fn records_results_like_enums() {
  let r: Result<i32, String> = Err("no".into());
  assert_eq!(
    recorded!(r),
    Value::table([("$variant", Value::str("Err")), ("0", Value::str("no"))])
  );
}

#[derive(Record)]
struct Point {
  x: i32,
  y: i32,
}

#[derive(Record)]
struct Meters(f64);

#[derive(Record)]
struct Pair(i32, &'static str);

#[derive(Record)]
struct Marker;

#[test]
fn records_structs() {
  assert_eq!(
    recorded!(Point { x: 1, y: -2 }),
    Value::table([("x", Value::Integer(1)), ("y", Value::Integer(-2))])
  );
  assert_eq!(
    recorded!(Meters(2.5)),
    Value::Array(vec![Value::Float(2.5)])
  );
  assert_eq!(
    recorded!(Pair(1, "a")),
    Value::Array(vec![Value::Integer(1), Value::str("a")])
  );
  assert_eq!(recorded!(Marker), Value::str("Marker"));
}

#[derive(Record)]
enum Color {
  Red,
  #[pmdb(rename = "GREEN")]
  Green,
}

#[derive(Record)]
enum Shape {
  Empty,
  Circle { radius: f64 },
  Rectangle(f64, f64),
}

#[test]
fn records_enums() {
  assert_eq!(recorded!(Color::Red), Value::str("Red"));
  assert_eq!(recorded!(Color::Green), Value::str("GREEN"));

  assert_eq!(
    recorded!(Shape::Empty),
    Value::table([("$variant", Value::str("Empty"))])
  );
  assert_eq!(
    recorded!(Shape::Circle { radius: 1.0 }),
    Value::table([
      ("$variant", Value::str("Circle")),
      ("radius", Value::Float(1.0))
    ])
  );
  assert_eq!(
    recorded!(Shape::Rectangle(1.0, 2.0)),
    Value::table([
      ("$variant", Value::str("Rectangle")),
      ("0", Value::Float(1.0)),
      ("1", Value::Float(2.0)),
    ])
  );
}

fn hidden(_: &String, w: ValueWriter<'_>) {
  w.string("***")
}

#[derive(Record)]
struct Account<T> {
  #[pmdb(rename = "user")]
  name: String,
  #[pmdb(with = hidden)]
  password: String,
  #[pmdb(skip)]
  #[allow(dead_code)]
  cache: Vec<u8>,
  balance: T,
  r#type: u8,
}

#[test]
fn applies_field_attributes_and_generic_bounds() {
  let a = Account {
    name: "ann".into(),
    password: "secret".into(),
    cache: vec![],
    balance: Meters(3.0),
    r#type: 1,
  };
  assert_eq!(
    recorded!(a),
    Value::table([
      ("user", Value::str("ann")),
      ("password", Value::str("***")),
      ("balance", Value::Array(vec![Value::Float(3.0)])),
      ("type", Value::Integer(1)),
    ])
  );
}

#[derive(Debug)]
#[allow(dead_code)]
struct Opaque {
  n: i32,
}

struct Unprintable;

#[derive(Record)]
struct Mixed {
  debug: Opaque,
  other: Unprintable,
  elapsed: std::time::Duration,
}

#[test]
fn records_types_that_do_not_opt_in_by_name() {
  // `Opaque` implements `Debug` and `Duration` implements `Debug` and `Serialize`, but neither
  // implements `Record`.
  assert_eq!(
    recorded!(Opaque { n: 1 }),
    Value::str("<values::Opaque object>")
  );
  assert_eq!(
    recorded!(Mixed {
      debug: Opaque { n: 2 },
      other: Unprintable,
      elapsed: Default::default()
    }),
    Value::table([
      ("debug", Value::str("<values::Opaque object>")),
      ("other", Value::str("<values::Unprintable object>")),
      ("elapsed", Value::str("<core::time::Duration object>")),
    ])
  );
}

#[derive(Record)]
struct Node {
  value: i32,
  next: Option<Rc<RefCell<Node>>>,
}

#[test]
fn records_cycles_once() {
  let a = Rc::new(RefCell::new(Node {
    value: 1,
    next: None,
  }));
  let b = Rc::new(RefCell::new(Node {
    value: 2,
    next: Some(a.clone()),
  }));
  a.borrow_mut().next = Some(b.clone());

  assert_eq!(
    recorded!(a),
    Value::table([
      ("value", Value::Integer(1)),
      (
        "next",
        Value::table([
          ("value", Value::Integer(2)),
          ("next", Value::str("<cycle>"))
        ])
      ),
    ])
  );
  a.borrow_mut().next = None;
}

struct Short;

impl Record for Short {
  fn record(&self, w: ValueWriter<'_>) {
    // Announces more contents than it writes.
    let mut a = w.array(2);
    let mut t = a.element().table(2);
    t.entry("k").integer(1);
  }
}

#[test]
fn pads_incomplete_values() {
  assert_eq!(
    recorded!(Short),
    Value::Array(vec![
      Value::table([("k", Value::Integer(1)), ("$missing0", Value::Null)]),
      Value::Null
    ])
  );
}

#[derive(Record)]
enum Writers {
  Fields { w: i32, t: i32, a: i32 },
}

#[test]
fn does_not_confuse_fields_with_writers() {
  assert_eq!(
    recorded!(Writers::Fields { w: 1, t: 2, a: 3 }),
    Value::table([
      ("$variant", Value::str("Fields")),
      ("w", Value::Integer(1)),
      ("t", Value::Integer(2)),
      ("a", Value::Integer(3)),
    ])
  );
}
