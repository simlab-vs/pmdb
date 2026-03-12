import Archivist

/// A tag identifying the type of a value.
public enum ValueTag: UInt8, Hashable, Sendable {

  case integer  = 0x01

  case float    = 0x02

  case string   = 0x03

  case array    = 0x04

  case table    = 0x05

  case function = 0xfe

  case object   = 0xff

}

/// A value stored in a trace.
public enum Value: Hashable, Sendable {

  /// A signed integer.
  case integer(Int64)

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
  case object(ContiguousArray<UInt8>)

  /// Creates a truthy value if `b` is `true` or a falsy value otherwise.
  public init(_ b: Bool) {
    self = .integer(b ? 1 : 0)
  }

  /// A textual description of the type of this value.
  public var type: String {
    switch self {
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

  /// Returns `true` iff `self` is interpreted as a truthy value when it appears as a condition.
  public var isTruthy: Bool {
    switch self {
    case .integer(let v):
      return v != 0
    case .float(let v):
      return v != 0.0
    case .string(let v):
      return !v.isEmpty
    case .array(let v):
      return !v.isEmpty
    case .table(let v):
      return !v.isEmpty
    case .lambda, .function, .object:
      return false
    }
  }

}

extension Value: Archivable {

  public init<T>(from archive: inout ReadableArchive<T>, in context: inout Any) throws {
    switch try archive.readByte() {
    case ValueTag.integer.rawValue:
      self = try .integer(archive.readSignedLEB128(as: Int64.self))

    case ValueTag.string.rawValue:
      self = try .string(archive.read(String.self))

    case ValueTag.function.rawValue:
      self = try .function(archive.read(String.self))

    case ValueTag.object.rawValue:
      let n = try archive.readUnsignedLEB128()
      var d: ContiguousArray<UInt8> = []
      d.reserveCapacity(Int(n))
      for _ in 0 ..< n { try d.append(archive.readByte()) }
      self = .object(d)

    default:
      throw ArchiveError.invalidInput
    }
  }

  public func write<T>(to archive: inout Archivist.WriteableArchive<T>, in context: inout Any) {
    fatalError("not implemented")
  }

}

extension Value: CustomStringConvertible {

  public var description: String {
    switch self {
    case .integer(let v):
      return v.description
    case .float(let v):
      return v.description
    case .string(let v):
      return v
    case .array(let v):
      return v.description
    case .table(let v):
      return "{\(v.map(String.init(describing:)).joined(separator: ", "))}"
    case .lambda(let d, _):
      return d.description
    case .function:
      return "<function>"
    case .object:
      return "<object>"
    }
  }

}
