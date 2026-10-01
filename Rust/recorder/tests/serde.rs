mod common;

use common::{Value, decode_value};
use pmdb_recorder::Record;
use pmdb_recorder::serde::Serde;
use serde::Serialize;
use std::collections::{BTreeMap, HashSet};

fn recorded<T: Serialize>(x: T) -> Value {
  decode_value(&pmdb_recorder::__private::encode(|w| Serde(x).record(w)))
}

#[derive(Serialize)]
struct Point {
  x: i32,
  #[serde(rename = "Y")]
  y: i32,
  #[serde(skip_serializing_if = "Option::is_none")]
  z: Option<i32>,
}

#[derive(Serialize)]
enum Shape {
  Empty,
  Circle { radius: f64 },
  Square(f64),
  Rectangle(f64, f64),
}

#[derive(Serialize)]
struct Meters(f64);

#[derive(Serialize)]
struct Flattened {
  a: i32,
  #[serde(flatten)]
  rest: BTreeMap<String, i32>,
}

#[test]
fn maps_the_serde_data_model() {
  use Value::{Float as F, Integer as I};
  assert_eq!(
    recorded(Point {
      x: 1,
      y: 2,
      z: None
    }),
    Value::table([("x", I(1)), ("Y", I(2))])
  );
  assert_eq!(recorded(Meters(1.0)), Value::Array(vec![F(1.0)]));
  assert_eq!(recorded(Shape::Empty), Value::str("Empty"));
  assert_eq!(
    recorded(Shape::Circle { radius: 1.0 }),
    Value::table([("$variant", Value::str("Circle")), ("radius", F(1.0))])
  );
  assert_eq!(
    recorded(Shape::Square(2.0)),
    Value::table([("$variant", Value::str("Square")), ("0", F(2.0))])
  );
  assert_eq!(
    recorded(Shape::Rectangle(1.0, 2.0)),
    Value::table([
      ("$variant", Value::str("Rectangle")),
      ("0", F(1.0)),
      ("1", F(2.0))
    ])
  );
  assert_eq!(
    recorded(u64::MAX),
    Value::Object(u128::from(u64::MAX).to_le_bytes().to_vec())
  );
  assert_eq!(recorded(serde_bytes_like()), Value::Object(vec![1, 2]));
  assert_eq!(
    recorded(BTreeMap::from([(1, 2)])),
    Value::Array(vec![Value::Array(vec![I(1), I(2)])])
  );
  assert_eq!(recorded(HashSet::from([7])), Value::Array(vec![I(7)]));

  // Flattening serializes a map of unknown length.
  assert_eq!(
    recorded(Flattened {
      a: 1,
      rest: BTreeMap::from([("b".into(), 2)])
    }),
    Value::table([("a", I(1)), ("b", I(2))])
  );
}

/// Returns a value serialized as bytes.
fn serde_bytes_like() -> impl Serialize {
  struct Bytes;
  impl Serialize for Bytes {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
      s.serialize_bytes(&[1, 2])
    }
  }
  Bytes
}

#[derive(Serialize)]
struct Inner {
  x: i32,
}

#[derive(Record)]
struct Outer {
  #[pmdb(with = pmdb_recorder::serde::record)]
  inner: Inner,
  elapsed: std::time::Duration,
}

#[test]
fn records_serializable_fields_only_when_asked_to() {
  let v = recorded_with_record(Outer {
    inner: Inner { x: 1 },
    elapsed: Default::default(),
  });
  assert_eq!(
    v,
    Value::table([
      ("inner", Value::table([("x", Value::Integer(1))])),
      ("elapsed", Value::str("<core::time::Duration object>")),
    ])
  );
}

fn recorded_with_record<T: Record>(x: T) -> Value {
  decode_value(&pmdb_recorder::__private::encode(|w| x.record(w)))
}

#[test]
fn records_values_of_failing_implementations() {
  struct Failing;
  impl Serialize for Failing {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
      use serde::ser::{Error, SerializeStruct};
      let mut t = s.serialize_struct("Failing", 2)?;
      t.serialize_field("a", &1)?;
      Err(S::Error::custom("failure"))
    }
  }
  assert_eq!(
    recorded(Failing),
    Value::table([("a", Value::Integer(1)), ("$missing0", Value::Null)])
  );
}
