/// An error that occurred during the execution of a command.
public struct RuntimeError: Error, CustomStringConvertible {

  /// A diagnostic of the error.
  public let description: String

  /// Creates an instance with the given properties.
  public init(_ description: String) {
    self.description = description
  }

}
