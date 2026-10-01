//! The recording of observations and their serialization as a trace.

use crate::__private::resolve;
use crate::archive::{write_string, write_unsigned};
use crate::value::{Encoder, Record};
use std::collections::HashMap;
use std::hash::{BuildHasher, Hasher, RandomState};
use std::panic::Location;
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::thread::ThreadId;

/// The tag of a snap in the binary format.
const SNAP: u8 = 0x01;

/// The tag of a call in the binary format.
const CALL: u8 = 0x02;

/// Instrumentation for tracing the execution of a Rust program.
///
/// A recorder can be shared by several threads. The observations made by each thread are attached
/// to the call that this thread is executing, so that the calls made by a thread are recorded as
/// children of the root unless they occur within a recorded call made by that same thread.
pub struct Recorder {
  state: Mutex<State>,
}

struct State {
  /// The unique identifier of the trace.
  identifier: [u8; 16],

  /// The number of observations recorded so far.
  count: usize,

  /// The encoding of the observations recorded so far.
  observations: Vec<u8>,

  /// The index of each observation's parent.
  parent: Vec<usize>,

  /// The index of the call that each thread is executing, if it isn't the root.
  active: HashMap<ThreadId, usize>,
}

impl Recorder {
  /// Creates an instance whose root is located where this method is called.
  #[track_caller]
  pub fn new() -> Self {
    Self::with_identifier(random_identifier())
  }

  /// Creates an instance identified by `identifier` whose root is located where this method is
  /// called.
  #[track_caller]
  pub fn with_identifier(identifier: [u8; 16]) -> Self {
    Self::rooted_at(Location::caller(), identifier)
  }

  /// Creates an instance identified by `identifier` whose root is located at `location`, whose
  /// path is resolved against the ancestors of the current directory.
  fn rooted_at(location: &'static Location<'static>, identifier: [u8; 16]) -> Self {
    let mut s = State {
      identifier,
      count: 0,
      observations: Vec::new(),
      parent: Vec::new(),
      active: HashMap::new(),
    };
    s.push(
      0,
      observation(
        CALL,
        resolve(location.file(), None),
        location.line(),
        |out| {
          write_string(out, "root");
          write_unsigned(out, 0);
          write_unsigned(out, 0);
        },
      ),
    );
    Self {
      state: Mutex::new(s),
    }
  }

  /// Records `value` with the given `label` where this method is called.
  ///
  /// The path of the source file is resolved against the ancestors of the current directory,
  /// whereas [`snap!`](crate::snap) resolves it against the directory of the crate using it.
  #[track_caller]
  pub fn snapshot<T: Record + ?Sized>(&self, label: &str, value: &T) {
    let l = Location::caller();
    let value = Encoder::encode(|w| value.record(w));
    self.snapshot_encoded(resolve(l.file(), None), l.line(), Some(label), value);
  }

  /// Records the value whose encoding is `value` with the given `label` at the given line.
  pub(crate) fn snapshot_encoded(
    &self, file: &str, line: u32, label: Option<&str>, value: Vec<u8>,
  ) {
    let o = snap(file, line, label, &value);
    let mut s = self.lock();
    let p = s.active();
    s.push(p, o);
  }

  /// Records a call to `function` with the given encoded arguments, and makes it the active call
  /// of the current thread.
  pub(crate) fn step_into(&self, file: &str, line: u32, function: &str, arguments: &[Vec<u8>]) {
    let o = observation(CALL, file, line, |out| {
      write_string(out, function);
      write_unsigned(out, arguments.len() as u64);
      for a in arguments {
        out.extend_from_slice(a);
      }
      write_unsigned(out, 0);
    });
    let mut s = self.lock();
    let p = s.active();
    let i = s.push(p, o);
    s.active.insert(std::thread::current().id(), i);
  }

  /// Makes the parent of the current thread's active call active again, and records `result`
  /// with the given `label` in that parent.
  pub(crate) fn step_out(&self, file: &str, line: u32, label: &str, result: Vec<u8>) {
    let o = snap(file, line, Some(label), &result);
    let mut s = self.lock();
    let a = s.active();
    assert_ne!(a, 0, "cannot step out of the root");
    let p = s.parent[a];
    if p == 0 {
      s.active.remove(&std::thread::current().id());
    } else {
      s.active.insert(std::thread::current().id(), p);
    }
    s.push(p, o);
  }

  /// Returns the trace recorded so far, in the binary format read by `pmdb`.
  pub fn serialize(&self) -> Vec<u8> {
    let s = self.lock();
    let mut out = Vec::with_capacity(s.observations.len() + s.parent.len() + 32);

    // The header is a magic number followed by a version number and the trace's identifier.
    out.extend_from_slice(b"pmdb");
    out.extend_from_slice(&[1, 0]);
    out.extend_from_slice(&s.identifier);

    // The number of observations followed by their values and the index of their parents.
    write_unsigned(&mut out, s.count as u64);
    out.extend_from_slice(&s.observations);
    for &p in &s.parent {
      write_unsigned(&mut out, p as u64);
    }
    out
  }

  /// Writes the trace recorded so far at `path`.
  pub fn write_to(&self, path: impl AsRef<std::path::Path>) -> std::io::Result<()> {
    std::fs::write(path, self.serialize())
  }

  fn lock(&self) -> MutexGuard<'_, State> {
    // A panic can't leave the state inconsistent: observations are encoded before being pushed.
    self.state.lock().unwrap_or_else(|e| e.into_inner())
  }
}

impl Default for Recorder {
  #[track_caller]
  fn default() -> Self {
    Self::new()
  }
}

impl State {
  /// Returns the index of the active call of the current thread.
  fn active(&self) -> usize {
    self
      .active
      .get(&std::thread::current().id())
      .copied()
      .unwrap_or(0)
  }

  /// Appends the observation encoded as `o` as a child of `parent` and returns its index.
  fn push(&mut self, parent: usize, o: Vec<u8>) -> usize {
    self.observations.extend_from_slice(&o);
    self.parent.push(parent);
    self.count += 1;
    self.count - 1
  }
}

/// Returns the encoding of an observation tagged by `tag` at the given line, whose remaining fields
/// are written by `contents`.
fn observation(tag: u8, file: &str, line: u32, contents: impl FnOnce(&mut Vec<u8>)) -> Vec<u8> {
  let mut out = vec![tag];
  write_string(&mut out, file);
  write_unsigned(&mut out, line as u64);
  contents(&mut out);
  out
}

/// Returns the encoding of a snap of `value` labeled by `label` at the given line.
fn snap(file: &str, line: u32, label: Option<&str>, value: &[u8]) -> Vec<u8> {
  observation(SNAP, file, line, |out| {
    match label {
      Some(l) => {
        out.push(1);
        write_string(out, l);
      }
      None => out.push(0),
    }
    out.extend_from_slice(value);
  })
}

/// Returns a random version 4 UUID.
fn random_identifier() -> [u8; 16] {
  // `RandomState` is seeded randomly for each instance, which suffices to tell traces apart
  // without depending on a random number generator.
  let mut bytes = [0u8; 16];
  for (i, chunk) in bytes.chunks_mut(8).enumerate() {
    let mut h = RandomState::new().build_hasher();
    h.write_usize(i);
    h.write_u128(
      std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos()),
    );
    chunk.copy_from_slice(&h.finish().to_le_bytes());
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  bytes
}

/// Returns the recorder used by `#[record]` and `snap!` unless another one is specified.
///
/// The root of its trace is located where it is first accessed.
#[track_caller]
pub fn main() -> &'static Recorder {
  static MAIN: OnceLock<Recorder> = OnceLock::new();
  let location = Location::caller();
  MAIN.get_or_init(|| Recorder::rooted_at(location, random_identifier()))
}
