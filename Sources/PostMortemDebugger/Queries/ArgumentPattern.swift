/// A pattern for matching one or several arguments.
public enum ArgumentPattern: Hashable, Sendable {

  /// Matches any number of named and positional arguments, ignoring their values.
  case universal

  /// Matches a single positional argument, optionally binding its value
  case positional(binding: String?)

  /// Matches a single positional argument equal to the given value.
  case positionalLiteral(Value)

  /// Matches any number of positional arguments, optionally binding the list values.
  case positionalVariadic(binding: String?)

  /// Matches a single named argument, optionally binding its value.
  case named(label: String, binding: String?)

  /// Matches a single named argument equal to the given value.
  case namedLiteral(label: String, value: Value)

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
    case .positionalLiteral(let v):
      return Self.literal(v)
    case .positionalVariadic(let b):
      return "\(b ?? "")*"
    case .named(let l, let b):
      return "\(l) = \(b ?? "_")"
    case .namedLiteral(let l, let v):
      return "\(l) = \(Self.literal(v))"
    case .namedVariadic(let b):
      return "\(b ?? "")**"
    }
  }

  /// Returns the literal denoting `v`, which is a value that can be written as a literal.
  private static func literal(_ v: Value) -> String {
    if case .string(let s) = v {
      let escaped = s.map({ (c) -> String in
        switch c {
        case "\n": "\\n"
        case "\t": "\\t"
        case "\\", "\"": "\\\(c)"
        default: String(c)
        }
      })
      return "\"\(escaped.joined())\""
    } else {
      return v.description
    }
  }

}
