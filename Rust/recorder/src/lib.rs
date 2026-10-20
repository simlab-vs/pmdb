//! Instrumentation for recording traces of Rust programs that can be explored with `pmdb`.
//!
//! Calls to functions annotated with [`record`] are recorded, together with their arguments and
//! results, and [`snap!`] records the value of an expression:
//!
//! ```
//! use pmdb_recorder as pmdb;
//!
//! #[pmdb::record]
//! fn factorial(n: u64) -> u64 {
//!   if n < 2 { 1 } else { n * factorial(n - 1) }
//! }
//!
//! let n = factorial(3);
//! pmdb::snap!(n);
//! let trace: Vec<u8> = pmdb::main().serialize();
//! ```
//!
//! Values are recorded according to their implementation of [`Record`], which can be derived.
//! The values of other types are recorded as a string naming their type, except closures, which
//! are recorded as functions. With the `serde` feature, `serde::Serde` records values of types
//! implementing `serde::Serialize`, e.g., in a field marked `#[pmdb(with = ...)]`.

mod archive;
mod recorder;
mod value;

#[cfg(feature = "serde")]
pub mod serde;

#[doc(hidden)]
#[path = "private.rs"]
pub mod __private;

pub use recorder::{Recorder, main};
pub use value::{ArrayWriter, Record, TableWriter, Tag, VARIANT_KEY, ValueWriter};

/// Records each call to the annotated function in a trace.
///
/// Each call is recorded with its arguments, followed by a snap labeled `<function>.$result`
/// holding the value it returns, or by a snap labeled `<function>.$exception` holding a table
/// with the `type` (i.e., `"panic"`) and `message` of the panic it raises. Arguments and results
/// are recorded in the state they have when they are observed, i.e., before and after the call.
/// Both the call and its outcome are located where the function is called.
///
/// The name of a function is its path relative to its module (e.g., `Type::method`).
///
/// # Options
///
/// - `recorder = <expr>`, where `<expr>` is a `&Recorder`, records calls in that recorder rather
///   than in [`main()`].
/// - `name = "<name>"` records calls under the given name.
///
/// # Limitations
///
/// `async` functions and `const` functions can't be recorded.
pub use pmdb_recorder_macros::record;

/// Derives an implementation of [`Record`].
///
/// - Structs with named fields are recorded as tables.
/// - Structs with unnamed fields are recorded as arrays.
/// - Unit structs are recorded as their name.
/// - Enums whose variants have no fields are recorded as the name of their variant.
/// - Other enums are recorded as tables mapping `$variant` to the name of their variant and each
///   field to its value. Unnamed fields are keyed by their position.
///
/// Fields whose type doesn't implement `Record` are recorded as a string naming their type.
///
/// # Attributes
///
/// - `#[pmdb(skip)]` on a field omits it.
/// - `#[pmdb(rename = "<name>")]` on a field or variant records it under another name.
/// - `#[pmdb(with = <path>)]` on a field records it with `<path>(&field, writer)`, where `writer`
///   is a [`ValueWriter`].
pub use pmdb_recorder_macros::Record;

/// Records the value of an expression in [`main()`], where this macro is used.
///
/// `snap!(label, value)` records `value` with the given label, and `snap!(x)` records the value
/// of `x` labeled by the text of the expression `x`. Values whose type doesn't implement
/// [`Record`] are recorded as a string naming their type.
#[macro_export]
macro_rules! snap {
  ($label:expr, $value:expr $(,)?) => {
    $crate::__private::snap($crate::main(), ::std::env!("CARGO_MANIFEST_DIR"), $label, {
      #[allow(unused_imports)]
      use $crate::__private::probe::*;
      $crate::__private::encode(|w| (&Probe(&$value)).__pmdb_record(w))
    })
  };
  ($value:expr $(,)?) => {
    $crate::snap!(stringify!($value), $value)
  };
}
