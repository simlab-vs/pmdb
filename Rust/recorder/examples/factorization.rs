//! The examples of `Python/main.py`, recorded in Rust.
//!
//! Run with `cargo run --example factorization -- <trace>` and explore the trace with
//! `pmdb <trace>`.

use pmdb_recorder::{self as pmdb, Record, record};

/// A slice of a vector.
#[derive(Record)]
struct Sublist<'a> {
  base: &'a mut Vec<i64>,
  lower: usize,
  upper: usize,
}

impl Sublist<'_> {
  /// Reorders the contents of `self` so that elements satisfying `in_first_part` occur first and
  /// returns the position immediately after the last element satisfying `in_first_part`.
  #[record]
  fn partition(&mut self, in_first_part: impl Fn(i64) -> bool) -> usize {
    let mut i = self.lower;
    while i != self.upper && in_first_part(self.base[i]) {
      i += 1;
    }
    let mut j = i + 1;
    while j < self.upper {
      if in_first_part(self.base[j]) {
        self.base.swap(i, j);
        i += 1;
      }
      j += 1;
    }
    i
  }

  /// Sorts the contents of `self` in increasing order.
  #[record]
  fn quicksort(&mut self) {
    if self.upper - self.lower <= 1 {
      return;
    }
    let p = self.base[self.upper - 1];
    let (lower, upper) = (self.lower, self.upper);
    let m = Sublist {
      base: self.base,
      lower,
      upper: upper - 1,
    }
    .partition(|x| x < p);
    self.base.swap(m, upper - 1);
    Sublist {
      base: self.base,
      lower,
      upper: m,
    }
    .quicksort();
    Sublist {
      base: self.base,
      lower: m + 1,
      upper,
    }
    .quicksort();
  }
}

/// Returns the greatest common divisor of positive integers `a` and `b`.
#[record]
fn gcd(a: i64, b: i64) -> i64 {
  if b == 0 { a } else { gcd(b, a % b) }
}

/// The outcome of a search for a factor.
#[derive(Record)]
enum Factor {
  Found { factor: i64 },
  Failed,
}

/// Returns a non-trivial factor of the positive integer `n` using Pollard's rho algorithm.
#[record]
fn rho(n: i64) -> Factor {
  let g = |x: i64| (x * x + 1) % n;

  #[record]
  fn f(n: i64, x: i64, y: i64, d: i64, g: &dyn Fn(i64) -> i64) -> Factor {
    if d == 1 {
      let (x, y) = (g(x), g(g(y)));
      f(n, x, y, gcd((x - y).abs(), n), g)
    } else if d != n {
      Factor::Found { factor: d }
    } else {
      Factor::Failed
    }
  }

  f(n, 2, 2, 1, &g)
}

fn main() -> std::io::Result<()> {
  let path = std::env::args()
    .nth(1)
    .unwrap_or_else(|| "factorization.trace".into());

  let mut xs = vec![1, 8, 3, 2, 6, 5, 7, 9, 4];
  let n = xs.len();
  Sublist {
    base: &mut xs,
    lower: 0,
    upper: n,
  }
  .quicksort();
  pmdb::snap!(xs);

  let factor = rho(10403);
  pmdb::snap!("factor", factor);

  pmdb::main().write_to(path)
}
