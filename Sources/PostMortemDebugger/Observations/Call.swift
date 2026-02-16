import Archivist

/// A record of a function application.
public struct Call: Observation {

  /// The source location to which this observation is attached.
  public let location: SourceLine

  /// The name of the function having been called.
  public let function: String

  /// The list of positional arguments.
  public let positional: [Value]

  /// The list of named arguments.
  public let named: [String: Value]

  /// The children of this objservation.
  public private(set) var children: [Int]

  /// Reads an instance from `archive`.
  public init<T>(from archive: inout ReadableArchive<T>) throws {
    self.location = try archive.read(SourceLine.self)
    self.function = try archive.read(String.self)
    self.children = []

    // Parse the positional arguments.
    let m = try Int(archive.readUnsignedLEB128())
    var positional: [Value] = .init(minimumCapacity: m)
    for _ in 0 ..< m {
      try positional.append(archive.read(Value.self))
    }
    self.positional = positional

    // Parse the named arguments.
    let n = try Int(archive.readUnsignedLEB128())
    var named: [String: Value] = .init(minimumCapacity: n)
    for _ in 0 ..< n {
      let k = try archive.read(String.self)
      let v = try archive.read(Value.self)
      if named.updateValue(v, forKey: k) != nil {
        throw ArchiveError.invalidInput
      }
    }
    self.named = named
  }

  /// Appends a nested observation to `self`.
  public mutating func append(_ child: Int) {
    children.append(child)
  }

}

extension Call: CustomStringConvertible {

  public var description: String {
    var arguments: [String] = []
    for p in positional {
      arguments.append(String(describing: p))
    }
    for n in named.sorted(by: { (a, b) in a.key < b.key }) {
      arguments.append("\(n.key): \(n.value)")
    }
    return "call \(function)(\(arguments.joined(separator: ", ")))"
  }

}
