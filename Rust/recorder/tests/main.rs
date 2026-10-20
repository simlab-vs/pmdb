//! Tests of the main recorder, which are in their own binary since it is global.

mod common;

use common::{Observation, Value, decode};
use pmdb_recorder::{self as pmdb, record};

#[record]
fn gcd(a: u64, b: u64) -> u64 {
  if b == 0 { a } else { gcd(b, a % b) }
}

#[test]
fn records_in_the_main_recorder() {
  let line = line!() + 1;
  let x = gcd(12, 18);
  pmdb::snap!(x);
  pmdb::snap!("twice", x * 2);

  let t = decode(&pmdb::main().serialize());
  assert_eq!(t.functions(), ["root", "gcd", "gcd", "gcd", "gcd"]);
  assert_eq!(t.snaps().last(), Some(&("twice", &Value::Integer(12))));
  assert_eq!(t.snap("x"), &Value::Integer(6));

  // The root is located where the main recorder is first used and snaps where they are taken.
  let Observation::Call { file, line: l, .. } = &t.observations[0] else {
    panic!()
  };
  assert_eq!(*l, line as u64);
  assert!(
    file.ends_with(file!()) && std::path::Path::new(file).is_file(),
    "{file}"
  );
  let Some(Observation::Snap { line: l, .. }) = t.observations.last() else {
    panic!()
  };
  assert_eq!(*l, line as u64 + 2);
}
