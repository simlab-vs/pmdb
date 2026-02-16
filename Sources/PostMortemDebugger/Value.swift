import Archivist

/// A tag identifying the type of a value.
public enum ValueTag: UInt8, Hashable, Sendable {

  case integer  = 0x01

  case float    = 0x02

  case string   = 0x03

  case function = 0xfe

  case object   = 0xff

}

/// A value stored in a trace.
public enum Value: Hashable, Sendable {

  /// A signed integer.
  case integer(Int64)

  /// A character string.
  case string(String)

  /// A function.
  case function(String)

  /// An arbitrary object.
  case object(ContiguousArray<UInt8>)

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
    case .string(let v):
      return v
    case .function:
      return "<function>"
    case .object:
      return "<object>"
    }
  }

}
