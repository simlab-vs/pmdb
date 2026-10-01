/// The precedence and associativity of an operator.
public enum PrecedenceGroup: UInt8 {

  /// The disjunction precedrence group, which is left associative.
  case disjunction = 0

  /// The conjunction precedrence group, which is left associative.
  case conjunction

  /// The comparison precedrence group, which is left associative.
  case comparison

  /// The addition precedrence group, which is left associative.
  case addition

  /// The multiplication precedrence group, which is left associative.
  case multiplication

  /// A value ordered after all precedence groups.
  case max

  /// Creates the precedence group containing `op`.
  public init<T: StringProtocol>(containing op: T) {
    switch op {
    case "*", "/", "%", "&":
      self = .multiplication
    case "+", "-", "|", "^":
      self = .addition
    case "==", "!=", "<", "<=", ">", ">=":
      self = .comparison
    case "&&":
      self = .conjunction
    case "||":
      self = .disjunction
    default:
      self = .addition
    }
  }

  /// The precedence group ordered right after `self`.
  public var next: PrecedenceGroup {
    .init(rawValue: rawValue + 1) ?? .max
  }

}

extension PrecedenceGroup: Hashable {}

extension PrecedenceGroup: Comparable {

  /// Returns `true` iff `l` binds less tightly than `r`.
  public static func < (l: Self, r: Self) -> Bool {
    l.rawValue < r.rawValue
  }

}
