import Archivist

/// A record of an expression having been evaluated.
public struct Snap: Observation {

  /// The source location to which this observation is attached.
  public let location: SourceLine

  /// A label identifying the snapshot.
  public let label: String?

  /// The result having been recorded.
  public let value: Value

  /// Creates an instance with the given properties.
  public init(location: SourceLine, label: String?, value: Value) {
    self.location = location
    self.label = label
    self.value = value
  }

  /// Reads an instance from `archive`, whose values may refer to the table of values `context`.
  public init<T>(from archive: inout ReadableArchive<T>, in context: inout Any) throws {
    self.location = try archive.read(SourceLine.self)
    self.label = try archive.read(String?.self)
    self.value = try archive.read(Value.self, in: &context)
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
