mod common;

use common::{Observation, Value, decode};
use pmdb_recorder::{Record, Recorder, record};
use std::sync::LazyLock;

/// Declares a recorder named `$name` for the functions of a single test, since tests run
/// concurrently.
macro_rules! recorder {
  ($name:ident) => {
    static $name: LazyLock<Recorder> = LazyLock::new(Recorder::new);
  };
}

recorder!(FACTORIAL);

#[record(recorder = &FACTORIAL)]
fn factorial(n: u64) -> u64 {
  if n < 2 { 1 } else { n * factorial(n - 1) }
}

#[test]
fn records_nested_calls() {
  assert_eq!(factorial(3), 6);
  let t = decode(&FACTORIAL.serialize());
  assert_eq!(
    t.tree(),
    "root[]
  factorial[Integer(3)]
    factorial[Integer(2)]
      factorial[Integer(1)]
      factorial.$result = Integer(1)
    factorial.$result = Integer(2)
  factorial.$result = Integer(6)
"
  );
}

recorder!(LOCATIONS);

#[record(recorder = &LOCATIONS)]
fn identity(x: i32) -> i32 {
  x
}

#[test]
fn locates_calls_where_they_are_made() {
  let line = line!() + 1;
  identity(1);
  let t = decode(&LOCATIONS.serialize());
  for o in &t.observations[1..] {
    let (Observation::Call { file, line: l, .. } | Observation::Snap { file, line: l, .. }) = o;
    assert_eq!(*l, line as u64);
    assert!(std::path::Path::new(file).is_absolute(), "{file}");
    assert!(file.ends_with(file!()), "{file}");
    assert!(std::path::Path::new(file).is_file());
  }
}

recorder!(METHODS);

#[derive(Record)]
struct Counter {
  count: i32,
}

trait Describe {
  fn describe(&self) -> String;
}

impl Counter {
  #[record(recorder = &METHODS)]
  fn bump(&mut self, by: i32) -> i32 {
    self.count += by;
    self.count
  }
}

impl Describe for Counter {
  #[record(recorder = &METHODS)]
  fn describe(&self) -> String {
    #[record(recorder = &METHODS)]
    fn helper() {}
    helper();
    format!("{}", self.count)
  }
}

#[test]
fn names_methods_and_records_receivers() {
  let mut c = Counter { count: 1 };
  c.bump(2);
  c.describe();
  let t = decode(&METHODS.serialize());
  assert_eq!(
    t.functions(),
    [
      "root",
      "Counter::bump",
      "Counter::describe",
      "Counter::describe::helper"
    ]
  );

  // The receiver is recorded in its state before the call.
  let count = |n| Value::table([("count", Value::Integer(n))]);
  assert_eq!(t.arguments("Counter::bump"), [count(1), Value::Integer(2)]);
  assert_eq!(t.arguments("Counter::describe"), [count(3)]);
  assert_eq!(t.snap("Counter::describe.$result"), &Value::str("3"));
}

recorder!(PANICS);

#[record(recorder = &PANICS)]
fn divide(a: i32, b: i32) -> i32 {
  if b == 0 {
    panic!("division of {a} by zero");
  }
  a / b
}

#[record(recorder = &PANICS)]
fn after() {}

#[test]
fn records_panics() {
  let r = std::panic::catch_unwind(|| divide(1, 0));
  assert!(r.is_err());
  after();
  let t = decode(&PANICS.serialize());
  assert_eq!(
    t.snap("divide.$exception"),
    &Value::table([
      ("type", Value::str("panic")),
      ("message", Value::str("division of 1 by zero"))
    ])
  );

  // The recorder is back at the root after the panic.
  assert_eq!(t.functions(), ["root", "divide", "after"]);
  assert_eq!(t.parent, [0, 0, 0, 0, 0]);
}

recorder!(SIGNATURES);

#[record(recorder = &SIGNATURES, name = "renamed")]
fn sum((a, b): (i32, i32), _: bool) -> Result<i32, String> {
  let c = a.checked_add(b).ok_or("overflow")?;
  Ok(c)
}

#[record(recorder = &SIGNATURES)]
fn evens(n: u32) -> impl Iterator<Item = u32> {
  (0..n).filter(|x| x % 2 == 0)
}

#[record(recorder = &SIGNATURES)]
fn first<T: std::fmt::Debug>(xs: &[T]) -> &T {
  &xs[0]
}

#[record(recorder = &SIGNATURES)]
fn apply(f: impl Fn(i32) -> i32, x: i32) -> i32 {
  f(x)
}

#[test]
fn supports_various_signatures() {
  assert_eq!(sum((1, 2), true), Ok(3));
  assert_eq!(evens(5).count(), 3);
  assert_eq!(first(&["a"]), &"a");
  assert_eq!(apply(|x| x + 1, 1), 2);

  let t = decode(&SIGNATURES.serialize());
  assert_eq!(
    t.functions(),
    ["root", "renamed", "evens", "first", "apply"]
  );
  assert_eq!(
    t.arguments("renamed"),
    [
      Value::Array(vec![Value::Integer(1), Value::Integer(2)]),
      Value::Integer(1)
    ]
  );
  assert_eq!(
    t.snap("renamed.$result"),
    &Value::table([("$variant", Value::str("Ok")), ("0", Value::Integer(3))])
  );

  // Values of generic types are recorded by name unless their bounds include `Record`.
  assert_eq!(t.arguments("first"), [Value::str("<&[&str] object>")]);

  // Closures are recorded as functions named after the function defining them.
  assert_eq!(
    t.arguments("apply")[0],
    Value::Function("calls::supports_various_signatures".into())
  );
}

recorder!(THREADS);

#[record(recorder = &THREADS)]
fn work(n: u32) -> u32 {
  if n == 0 { 0 } else { work(n - 1) + 1 }
}

#[test]
fn attaches_calls_to_the_thread_making_them() {
  let hs: Vec<_> = (0..4).map(|_| std::thread::spawn(|| work(20))).collect();
  for h in hs {
    h.join().unwrap();
  }
  let t = decode(&THREADS.serialize());
  assert_eq!(t.observations.len(), 1 + 4 * 2 * 21);

  // The calls of each thread form a chain of 21 nested calls whose results are recorded in
  // their parents.
  for (i, o) in t.observations.iter().enumerate().skip(1) {
    let p = t.parent[i];
    match o {
      Observation::Call { positional, .. } => match &t.observations[p] {
        Observation::Call {
          function,
          positional: q,
          ..
        } if function == "work" => {
          assert_eq!(
            positional,
            &[Value::Integer(match q[0] {
              Value::Integer(n) => n - 1,
              _ => panic!(),
            })]
          );
        }
        Observation::Call { function, .. } => assert_eq!(function, "root"),
        _ => panic!(),
      },
      Observation::Snap {
        value: Value::Integer(n),
        ..
      } => match &t.observations[p] {
        Observation::Call { positional, .. } if p != 0 => {
          assert_eq!(positional, &[Value::Integer(n + 1)])
        }
        _ => assert_eq!((p, *n), (0, 20)),
      },
      o => panic!("{o:?}"),
    }
  }
}

recorder!(GENERICS);

struct Wrapper<'a, T>(&'a T);

impl<T: Record> Wrapper<'_, T> {
  #[record(recorder = &GENERICS)]
  fn get(&self) -> &T {
    self.0
  }
}

impl<T: Record> std::fmt::Display for Wrapper<'_, Vec<T>> {
  #[record(recorder = &GENERICS)]
  fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
    write!(f, "{}", self.0.len())
  }
}

#[test]
fn names_methods_of_generic_types_without_arguments() {
  Wrapper(&1).get();
  let _ = Wrapper(&vec![1]).to_string();
  let t = decode(&GENERICS.serialize());
  assert_eq!(t.functions(), ["root", "Wrapper::get", "Wrapper::fmt"]);
  assert_eq!(
    t.arguments("Wrapper::get"),
    [Value::str("<&calls::Wrapper<'_, i32> object>")]
  );
}

#[test]
fn simplifies_names() {
  use pmdb_recorder::__private::qualified_name as q;
  assert_eq!(q("m::f::_", "m"), "f");
  assert_eq!(q("m::S<'_, T>::f::{{closure}}::g::_", "m"), "S::f::g");
  assert_eq!(
    q("<m::S<Vec<u8>> as core::fmt::Display>::fmt::_", "m"),
    "S::fmt"
  );
  assert_eq!(q("other::f::_", "m"), "other::f");
}
