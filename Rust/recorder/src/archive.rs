//! Primitives writing the building blocks of the binary trace format.

/// Writes `n` using the unsigned LEB128 encoding.
pub(crate) fn write_unsigned(out: &mut Vec<u8>, mut n: u64) {
  loop {
    let b = (n & 0x7f) as u8;
    n >>= 7;
    if n == 0 {
      out.push(b);
      return;
    }
    out.push(b | 0x80);
  }
}

/// Writes `n` using the signed LEB128 encoding.
pub(crate) fn write_signed(out: &mut Vec<u8>, mut n: i128) {
  loop {
    let b = (n & 0x7f) as u8;
    n >>= 7;
    if (n == 0 && b & 0x40 == 0) || (n == -1 && b & 0x40 != 0) {
      out.push(b);
      return;
    }
    out.push(b | 0x80);
  }
}

/// Writes `n` using the signed LEB128 encoding.
pub(crate) fn write_signed_unsigned(out: &mut Vec<u8>, mut n: u128) {
  loop {
    let b = (n & 0x7f) as u8;
    n >>= 7;
    if n == 0 && b & 0x40 == 0 {
      out.push(b);
      return;
    }
    out.push(b | 0x80);
  }
}

/// Writes the UTF-8 code units of `s` prefixed by their number.
pub(crate) fn write_string(out: &mut Vec<u8>, s: &str) {
  write_unsigned(out, s.len() as u64);
  out.extend_from_slice(s.as_bytes());
}

#[cfg(test)]
mod tests {
  use super::*;

  fn unsigned(n: u64) -> Vec<u8> {
    let mut out = Vec::new();
    write_unsigned(&mut out, n);
    out
  }

  fn signed(n: i128) -> Vec<u8> {
    let mut out = Vec::new();
    write_signed(&mut out, n);
    out
  }

  fn signed_unsigned(n: u128) -> Vec<u8> {
    let mut out = Vec::new();
    write_signed_unsigned(&mut out, n);
    out
  }

  #[test]
  fn writes_unsigned_leb128() {
    assert_eq!(unsigned(0), [0x00]);
    assert_eq!(unsigned(127), [0x7f]);
    assert_eq!(unsigned(128), [0x80, 0x01]);
    assert_eq!(unsigned(624485), [0xe5, 0x8e, 0x26]);
    assert_eq!(unsigned(u64::MAX).len(), 10);
  }

  #[test]
  fn writes_signed_leb128() {
    assert_eq!(signed(0), [0x00]);
    assert_eq!(signed(63), [0x3f]);
    assert_eq!(signed(64), [0xc0, 0x00]);
    assert_eq!(signed(-1), [0x7f]);
    assert_eq!(signed(-64), [0x40]);
    assert_eq!(signed(-65), [0xbf, 0x7f]);
    assert_eq!(signed(-123456), [0xc0, 0xbb, 0x78]);
    assert_eq!(signed(i64::MIN.into()).len(), 10);
    assert_eq!(signed(i64::MAX.into()).len(), 10);
    assert_eq!(signed(i128::MIN).len(), 19);
  }

  #[test]
  fn writes_unsigned_integers_with_signed_leb128() {
    assert_eq!(signed_unsigned(63), [0x3f]);
    assert_eq!(signed_unsigned(64), [0xc0, 0x00]);
    assert_eq!(signed_unsigned(u128::MAX).len(), 19);
    assert_eq!(signed_unsigned(u128::MAX)[18], 0x03);
  }
}
