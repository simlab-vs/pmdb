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
  public let named: SortedDictionary<String, Value>

  /// The children of this objservation.
  public private(set) var children: [Int]

  /// Creates an instance with the given properties.
  public init(
    location: SourceLine, function: String,
    positional: [Value], named: SortedDictionary<String, Value>
  ) {
    self.location = location
    self.function = function
    self.positional = positional
    self.named = named
    self.children = []
  }

  /// Reads an instance from `archive`, where it was written with the name of the parameter of each
  /// positional argument and the location of the function's definition iff `withParameters`, and
  /// whose values may refer to the table of values `context`.
  public init<T>(
    from archive: inout ReadableArchive<T>, withParameters: Bool = false, in context: inout Any
  ) throws {
    self.location = try archive.read(SourceLine.self)
    self.function = try archive.read(String.self)
    self.children = []

    // Skip the location of the function's definition, if any.
    if withParameters { _ = try archive.read(SourceLine.self) }

    // Parse the positional arguments, skipping their parameters' names, if any.
    let m = try Int(archive.readUnsignedLEB128())
    var positional: [Value] = .init(minimumCapacity: m)
    for _ in 0 ..< m {
      if withParameters { _ = try archive.read(String.self) }
      try positional.append(archive.read(Value.self, in: &context))
    }
    self.positional = positional

    // Parse the named arguments.
    let n = try Int(archive.readUnsignedLEB128())
    var named: SortedDictionary<String, Value> = .init(minimumCapacity: n)
    for _ in 0 ..< n {
      let k = try archive.read(String.self)
      let v = try archive.read(Value.self, in: &context)
      try modify(&named[k]) { (w) in
        if w != nil { throw ArchiveError.invalidInput } else { w = .some(v) }
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
