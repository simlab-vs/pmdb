import Archivist

/// A line of a source file.
public struct SourceLine: Hashable, Sendable {

  /// The source file containing this line.
  public let source: String

  /// The 1-based index of this line.
  public let number: Int

  /// Creates an instance with the given properties.
  public init(_ number: Int, in source: String) {
    self.source = source
    self.number = number
  }

  /// Creates an instance with `gnu`, which is a URL and a 1-based line index separated by a colon.
  public init?(gnu: String) {
    guard
      let i = gnu.firstIndex(of: ":"),
      let n = Int(gnu[gnu.index(after: i)...])
    else { return nil }
    self.init(n, in: .init(gnu[..<i]))
  }

}

extension SourceLine: Archivable {

  public init<T>(from archive: inout ReadableArchive<T>, in context: inout Any) throws {
    self.source = try archive.read(String.self)
    self.number = Int(try archive.readUnsignedLEB128())
  }
  
  public func write<T>(to archive: inout WriteableArchive<T>, in context: inout Any) throws {
    try archive.write(source)
    archive.write(unsignedLEB128: number)
  }

}

extension SourceLine: CustomStringConvertible {

  public var description: String {
    "\(source):\(number)"
  }

}
