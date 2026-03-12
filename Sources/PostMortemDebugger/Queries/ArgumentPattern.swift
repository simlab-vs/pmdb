/// A pattern for matching one or several arguments.
public enum ArgumentPattern: Hashable, Sendable {

  /// Matches any number of named and positional arguments, ignoring their values.
  case universal

  /// Matches a single positional argument, optionally binding its value
  case positional(binding: String?)

  /// Matches any number of positional arguments, optionally binding the list values.
  case positionalVariadic(binding: String?)

  /// Matches a single named argument, optionally binding its value.
  case named(label: String, binding: String?)

  /// Matches any number of named arguments, optionally binding the key/value pairs.
  case namedVariadic(binding: String?)

  /// `true` iff `self` matches an arbitrary sequence of arguments without binding it.
  public var isUnboundVariadic: Bool {
    switch self {
    case .universal, .positionalVariadic(binding: nil), .namedVariadic(binding: nil):
      return true
    default:
      return false
    }
  }

}

extension ArgumentPattern: CustomStringConvertible {

  public var description: String {
    switch self {
    case .universal:
      return "..."
    case .positional(let b):
      return b ?? "_"
    case .positionalVariadic(let b):
      return "\(b ?? "")*"
    case .named(let l, let b):
      return "\(l) = \(b ?? "_")"
    case .namedVariadic(let b):
      return "\(b ?? "")**"
    }
  }

}
