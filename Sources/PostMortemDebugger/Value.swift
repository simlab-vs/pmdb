import Archivist
import BigInt

/// A tag identifying the type of a value.
public enum ValueTag: UInt8, Hashable, Sendable {

  case null     = 0x00

  case integer  = 0x01

  case float    = 0x02

  case string   = 0x03

  case array    = 0x04

  case table    = 0x05

  case boolean  = 0x06

  case function = 0xfe

  case object   = 0xff

}

/// A value stored in a trace.
public enum Value: Hashable, Sendable {

  /// The absence of a value (e.g., `None` in Python or `null` in JavaScript), written `none` in
  /// queries.
  ///
  /// This case isn't named `none` to avoid confusions with `Optional.none`.
  case null

  /// A Boolean.
  case boolean(Bool)

  /// A signed integer of arbitrary precision.
  case integer(BigInt)

  /// A floating-point number.
  case float(Double)

  /// A character string.
  case string(String)

  /// The result of matching an arbitrary sequence of positional arguments.
  case array([Value])

  /// The result of matching an arbitrary sequence of named arguments.
  case table(SortedDictionary<String, Value>)

  /// A term abstraction and its environment.
  case lambda(Expression.Lambda, [String: Value])

  /// A function.
  case function(String)

  /// An arbitrary object.
  case object([UInt8])

  /// Creates a Boolean value.
  public init(_ b: Bool) {
    self = .boolean(b)
  }

  /// A textual description of the type of this value.
  public var type: String {
    switch self {
    case .null: "none"
    case .boolean: "boolean"
    case .integer: "integer"
    case .float: "float"
    case .string: "string"
    case .array: "array"
    case .table: "table"
    case .lambda: "lambda"
    case .function: "function"
    case .object: "object"
    }
  }

}

extension Value: Archivable {

  public init<T>(from archive: inout ReadableArchive<T>, in context: inout Any) throws {
    switch try archive.readByte() {
    case ValueTag.null.rawValue:
      self = .null

    case ValueTag.boolean.rawValue:
      switch try archive.readByte() {
      case 0: self = .boolean(false)
      case 1: self = .boolean(true)
      default: throw ArchiveError.invalidInput
      }

    case ValueTag.integer.rawValue:
      self = try .integer(Self.readSignedLEB128(from: &archive))

    case ValueTag.float.rawValue:
      self = try .float(archive.read(Double.self, endianness: .little))

    case ValueTag.string.rawValue:
      self = try .string(archive.read(String.self))

    case ValueTag.array.rawValue:
      let n = try Int(archive.readUnsignedLEB128())
      var elements: [Value] = []
      elements.reserveCapacity(n)
      for _ in 0 ..< n { try elements.append(archive.read(Value.self)) }
      self = .array(elements)

    case ValueTag.table.rawValue:
      let n = try Int(archive.readUnsignedLEB128())
      var entries = SortedDictionary<String, Value>(minimumCapacity: n)
      for _ in 0 ..< n {
        let k = try archive.read(String.self)
        let v = try archive.read(Value.self)
        try modify(&entries[k]) { (w) in
          if w != nil { throw ArchiveError.invalidInput } else { w = .some(v) }
        }
      }
      self = .table(entries)

    case ValueTag.function.rawValue:
      self = try .function(archive.read(String.self))

    case ValueTag.object.rawValue:
      let n = try archive.readUnsignedLEB128()
      var d: [UInt8] = []
      d.reserveCapacity(Int(n))
      for _ in 0 ..< n { try d.append(archive.readByte()) }
      self = .object(d)

    default:
      throw ArchiveError.invalidInput
    }
  }

  /// Reads an integer of arbitrary precision encoded with the signed LEB128 encoding.
  private static func readSignedLEB128<T>(from archive: inout ReadableArchive<T>) throws -> BigInt {
    // Accumulate the first 63 bits in a machine integer, which is enough for most values.
    var bits: UInt64 = 0
    var wide = BigInt(0)
    var shift = 0
    while true {
      let b = try archive.readByte()
      if shift < 63 {
        bits |= UInt64(b & 0x7f) << shift
      } else {
        if shift == 63 { wide = BigInt(bits) }
        wide |= BigInt(b & 0x7f) << shift
      }
      shift += 7
      if b & 0x80 != 0 { continue }

      let negative = b & 0x40 != 0
      if shift <= 63 {
        let n = Int64(bitPattern: negative ? bits | (~0 << shift) : bits)
        return BigInt(n)
      } else {
        return negative ? wide - (BigInt(1) << shift) : wide
      }
    }
  }

  public func write<T>(to archive: inout Archivist.WriteableArchive<T>, in context: inout Any) {
    fatalError("not implemented")
  }

}

extension Value: CustomStringConvertible {

  public var description: String {
    switch self {
    case .null:
      return "none"
    case .boolean(let v):
      return v.description
    case .integer(let v):
      return v.description
    case .float(let v):
      return v.description
    case .string(let v):
      return v
    case .array(let v):
      return "[\(v.map(String.init(describing:)).joined(separator: ", "))]"
    case .table(let v):
      return "{\(v.map({ (e) in "\(e.key): \(e.value)" }).joined(separator: ", "))}"
    case .lambda(let d, _):
      return d.description
    case .function:
      return "<function>"
    case .object:
      return "<object>"
    }
  }

}

extension Value {

  /// The result of comparing two numbers.
  enum NumericOrder {

    /// The left operand is less than the right one.
    case less

    /// The operands are equal.
    case equal

    /// The left operand is greater than the right one.
    case greater

    /// One of the operands is NaN.
    case unordered

  }

  /// Returns how `self` compares to `other` by value iff both are numbers, or `nil` otherwise.
  ///
  /// Integers and floating-point numbers are compared exactly, without converting one to the
  /// other.
  func numericOrder(_ other: Value) -> NumericOrder? {
    switch (self, other) {
    case (.integer(let a), .integer(let b)):
      return a < b ? .less : a > b ? .greater : .equal
    case (.float(let a), .float(let b)):
      return a < b ? .less : a > b ? .greater : a == b ? .equal : .unordered
    case (.integer(let a), .float(let b)):
      return Self.compare(a, b)
    case (.float(let a), .integer(let b)):
      switch Self.compare(b, a) {
      case .less: return .greater
      case .greater: return .less
      case let o: return o
      }
    default:
      return nil
    }
  }

  /// Returns how `a` compares to `b`.
  private static func compare(_ a: BigInt, _ b: Double) -> NumericOrder {
    if b.isNaN { return .unordered }
    if b.isInfinite { return b < 0 ? .greater : .less }
    let n = BigInt(exactly: b.rounded(.down))!
    if a < n { return .less }
    if a > n { return .greater }
    return b == b.rounded(.down) ? .equal : .less
  }

  /// Returns `true` iff `self` is equal to `other`.
  ///
  /// Numbers are equal iff they have the same value, NaN being equal to nothing. Arrays and tables
  /// are equal iff their contents are. Other values are equal iff they have the same type and
  /// contents, except lambdas, which are never equal.
  func isEqual(to other: Value) -> Bool {
    switch (self, other) {
    case (.integer, _), (.float, _):
      return numericOrder(other) == .equal
    case (.array(let a), .array(let b)):
      return a.count == b.count && zip(a, b).allSatisfy({ (x, y) in x.isEqual(to: y) })
    case (.table(let a), .table(let b)):
      return a.count == b.count
        && zip(a, b).allSatisfy({ (x, y) in x.key == y.key && x.value.isEqual(to: y.value) })
    case (.lambda, _):
      return false
    default:
      return self == other
    }
  }

}
