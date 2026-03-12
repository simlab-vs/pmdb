/// A diagnostic related to a region of a source input.
public struct Diagnostic: Hashable, Error {

  /// The severity of a diagnostic.
  public enum Level: String, Hashable, Sendable {

    /// An error that does not prevent compilation.
    case warning

    /// An unrecoverable error that prevents compilation.
    case error

  }

  /// The level of the diagnostic.
  public let level: Level

  /// The main description of the diagnostic.
  public let message: String

  /// The source code or source position (if empty) identified as the cause of the error.
  public let site: Range<String.Index>

  /// Creates an instance with the given properties.
  public init(_ level: Level, _ message: String, at site: Range<String.Index>) {
    self.level = level
    self.message = message
    self.site = site
  }

}
