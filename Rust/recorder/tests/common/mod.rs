//! A decoder of binary traces mirroring the one of `pmdb`, used to check what is recorded.

#![allow(dead_code)]

use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
  Null,
  Boolean(bool),
  Integer(i128),
  Float(f64),
  String(String),
  Array(Vec<Value>),
  Table(BTreeMap<String, Value>),
  Function(String),
  Object(Vec<u8>),
}

impl Value {
  pub fn str(s: &str) -> Value {
    Value::String(s.into())
  }

  pub fn table<const N: usize>(entries: [(&str, Value); N]) -> Value {
    Value::Table(
      entries
        .into_iter()
        .map(|(k, v)| (k.to_string(), v))
        .collect(),
    )
  }
}

#[derive(Debug, PartialEq)]
pub enum Observation {
  Snap {
    file: String,
    line: u64,
    label: Option<String>,
    value: Value,
  },
  Call {
    file: String,
    line: u64,
    function: String,
    positional: Vec<Value>,
    named: Vec<(String, Value)>,
  },
}

#[derive(Debug)]
pub struct Trace {
  pub identifier: [u8; 16],
  pub observations: Vec<Observation>,
  pub parent: Vec<usize>,
}

impl Trace {
  /// Returns the names of the recorded calls, in order.
  pub fn functions(&self) -> Vec<&str> {
    self
      .observations
      .iter()
      .filter_map(|o| match o {
        Observation::Call { function, .. } => Some(function.as_str()),
        _ => None,
      })
      .collect()
  }

  /// Returns the labels and values of the recorded snaps, in order.
  pub fn snaps(&self) -> Vec<(&str, &Value)> {
    self
      .observations
      .iter()
      .filter_map(|o| match o {
        Observation::Snap { label, value, .. } => Some((label.as_deref().unwrap_or(""), value)),
        _ => None,
      })
      .collect()
  }

  /// Returns the arguments of the first call to `f`.
  pub fn arguments(&self, f: &str) -> &[Value] {
    self
      .observations
      .iter()
      .find_map(|o| match o {
        Observation::Call {
          function,
          positional,
          ..
        } if function == f => Some(&positional[..]),
        _ => None,
      })
      .unwrap_or_else(|| panic!("no call to {f}"))
  }

  /// Returns the value of the first snap labeled `l`.
  pub fn snap(&self, l: &str) -> &Value {
    self
      .snaps()
      .into_iter()
      .find(|(m, _)| *m == l)
      .unwrap_or_else(|| panic!("no snap labeled {l}"))
      .1
  }

  /// Returns a textual tree of the observations, to compare traces in tests.
  pub fn tree(&self) -> String {
    let mut out = String::new();
    self.write(0, 0, &mut out);
    out
  }

  fn write(&self, i: usize, depth: usize, out: &mut String) {
    out.push_str(&"  ".repeat(depth));
    match &self.observations[i] {
      Observation::Snap { label, value, .. } => {
        out.push_str(&format!("{} = {value:?}\n", label.as_deref().unwrap_or("")))
      }
      Observation::Call {
        function,
        positional,
        ..
      } => out.push_str(&format!("{function}{positional:?}\n")),
    }
    for j in (i + 1)..self.parent.len() {
      if self.parent[j] == i {
        self.write(j, depth + 1, out);
      }
    }
  }
}

pub fn decode(bytes: &[u8]) -> Trace {
  let mut r = Reader { bytes, at: 0 };
  assert_eq!(r.take(4), b"pmdb");
  assert_eq!(r.take(2), [1, 0]);
  let identifier = r.take(16).try_into().unwrap();
  let count = r.unsigned() as usize;
  let observations = (0..count).map(|_| r.observation()).collect();
  let parent: Vec<usize> = (0..count).map(|_| r.unsigned() as usize).collect();
  assert_eq!(r.at, bytes.len(), "trailing bytes");

  // Validate parents the way `pmdb` does.
  for (i, &p) in parent.iter().enumerate() {
    if i == 0 {
      assert_eq!(p, 0);
    } else {
      assert!(p < i, "parent of {i} is {p}");
    }
  }
  Trace {
    identifier,
    observations,
    parent,
  }
}

/// Returns the value encoded as `bytes`.
pub fn decode_value(bytes: &[u8]) -> Value {
  let mut r = Reader { bytes, at: 0 };
  let v = r.value();
  assert_eq!(r.at, bytes.len(), "trailing bytes");
  v
}

struct Reader<'a> {
  bytes: &'a [u8],
  at: usize,
}

impl Reader<'_> {
  fn take(&mut self, n: usize) -> &[u8] {
    let s = &self.bytes[self.at..self.at + n];
    self.at += n;
    s
  }

  fn byte(&mut self) -> u8 {
    self.take(1)[0]
  }

  fn unsigned(&mut self) -> u64 {
    let (mut n, mut shift) = (0u64, 0);
    loop {
      let b = self.byte();
      n |= ((b & 0x7f) as u64) << shift;
      shift += 7;
      if b & 0x80 == 0 {
        return n;
      }
    }
  }

  fn signed(&mut self) -> i128 {
    let (mut n, mut shift) = (0i128, 0);
    loop {
      let b = self.byte();
      n |= ((b & 0x7f) as i128) << shift;
      shift += 7;
      if b & 0x80 == 0 {
        if shift < 128 && b & 0x40 != 0 {
          n |= -1 << shift;
        }
        return n;
      }
    }
  }

  fn string(&mut self) -> String {
    let n = self.unsigned() as usize;
    String::from_utf8(self.take(n).to_vec()).unwrap()
  }

  fn value(&mut self) -> Value {
    match self.byte() {
      0x00 => Value::Null,
      0x01 => Value::Integer(self.signed()),
      0x02 => Value::Float(f64::from_le_bytes(self.take(8).try_into().unwrap())),
      0x03 => Value::String(self.string()),
      0x04 => {
        let n = self.unsigned();
        Value::Array((0..n).map(|_| self.value()).collect())
      }
      0x06 => match self.byte() {
        0 => Value::Boolean(false),
        1 => Value::Boolean(true),
        b => panic!("invalid Boolean {b:#x}"),
      },
      0x05 => {
        let n = self.unsigned();
        let mut t = BTreeMap::new();
        for _ in 0..n {
          let k = self.string();
          let v = self.value();
          assert!(t.insert(k.clone(), v).is_none(), "duplicate key {k}");
        }
        Value::Table(t)
      }
      0xfe => Value::Function(self.string()),
      0xff => {
        let n = self.unsigned() as usize;
        Value::Object(self.take(n).to_vec())
      }
      t => panic!("invalid tag {t:#x}"),
    }
  }

  fn observation(&mut self) -> Observation {
    let tag = self.byte();
    let file = self.string();
    let line = self.unsigned();
    match tag {
      0x01 => {
        let label = match self.byte() {
          0 => None,
          1 => Some(self.string()),
          b => panic!("invalid label flag {b}"),
        };
        Observation::Snap {
          file,
          line,
          label,
          value: self.value(),
        }
      }
      0x02 => {
        let function = self.string();
        let n = self.unsigned();
        let positional = (0..n).map(|_| self.value()).collect();
        let m = self.unsigned();
        let named = (0..m).map(|_| (self.string(), self.value())).collect();
        Observation::Call {
          file,
          line,
          function,
          positional,
          named,
        }
      }
      t => panic!("invalid observation tag {t:#x}"),
    }
  }
}
