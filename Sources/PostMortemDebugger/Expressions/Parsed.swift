/// A construct whose representation was parsed from a source files.
public struct Parsed<T> {

  /// The site from which the expression was parsed.
  public let site: Range<String.Index>

  /// The parsed construct.
  public let value: T

  /// Creates an instance annotating its value with the site from which it was extracted.
  public init(_ value: T, at site: Range<String.Index>) {
    self.value = value
    self.site = site
  }

}

extension Parsed: Equatable where T: Equatable {}

extension Parsed: Hashable where T: Hashable {}

extension Parsed: Sendable where T: Sendable {}

extension Parsed: CustomStringConvertible {

  public var description: String {
    String(describing: value)
  }

}
