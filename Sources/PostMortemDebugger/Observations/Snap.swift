import Archivist

/// A record of an expression having been evaluated.
public struct Snap: Observation {

  /// The source location to which this observation is attached.
  public let location: SourceLine

  /// A label identifying the snapshot.
  public let label: String?

  /// The result having been recorded.
  public let value: Value

  /// Reads an instance from `archive`.
  public init<T>(from archive: inout ReadableArchive<T>) throws {
    self.location = try archive.read(SourceLine.self)
    self.label = try archive.read(String?.self)
    self.value = try archive.read(Value.self)
  }

}

extension Snap: CustomStringConvertible {

  public var description: String {
    if let l = label {
      return "snap \(l) = \(value)"
    } else {
      return "snap \(value)"
    }
  }

}
