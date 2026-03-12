/// A pattern for matching snapshot bindings and function names.
public enum IdentifierPattern: Hashable, Sendable {

  /// Matches any identifier.
  case wildcard

  /// Matches an identifier equal to a specified string.
  case exactly(String)

  /// Matches an identifier with a regular expression.
  case regex(String)

  /// Returns `true` iff `self` matches `s`.
  public func matches(_ s: String) -> Bool {
    switch self {
    case .wildcard:
      return true

    case .exactly(let literal):
      return s == literal

    case .regex(let literal):
      if let pattern = try? Regex(.init(literal.dropFirst().dropLast())) {
        return s.wholeMatch(of: pattern) != nil
      } else {
        return false
      }
    }
  }

}

extension IdentifierPattern: CustomStringConvertible {

  public var description: String {
    switch self {
    case .wildcard:
      return "_"
    case .exactly(let s), .regex(let s):
      return s
    }
  }

}
