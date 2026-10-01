/// A pattern for matching an argument list.
///
/// An argument pattern list describes how to bind arguments of a call observations. A match
/// results in either a binding mapping unification variables to argument values, or a failure,
/// indicating that the pattern does not match.
public struct ArgumentPatternList: Hashable, Sendable {

  /// The paterns of the arguments.
  public let patterns: [ArgumentPattern]

  /// Creates an instance with the given patterns.
  public init(_ patterns: [ArgumentPattern]) {
    assert(!patterns.contains(.universal) || patterns.count == 1)
    self.patterns = patterns
  }

  /// `true` iff `self` is empty.
  public var isEmpty: Bool {
    patterns.isEmpty
  }

  /// `true` iff `self` is the universal pattern, which matches any argument list.
  public var isUniversal: Bool {
    patterns == [.universal]
  }

  /// `true` iff `self` can match any argument list.
  public var isEquivalentToUniversal: Bool {
    if isUniversal { return true }

    var matchesPositional = false
    var matchesNamed = false
    for p in patterns {
      switch p {
      case .positionalVariadic(let b):
        if b == nil { matchesPositional = true } else { return false }
      case .namedVariadic(let b):
        if b == nil { matchesNamed = true } else { return false }
      default:
        return false
      }
    }
    return matchesPositional && matchesNamed
  }

  /// Returns `true` iff `self` matches the arguments of `o`, unifying variables in `environement`.
  public func matches(
    argumentsOf o: Call, in environment: inout [String: Value]
  ) -> Bool {
    matches(o.positional, o.named, in: &environment)
  }

  /// Returns `true` iff `self` matches the given arguments, unifying variables in `environement`.
  public func matches(
    _ positional: [Value], _ named: SortedDictionary<String, Value>,
    in environment: inout [String: Value]
  ) -> Bool {
    // Trivial if `self` is the universal pattern.
    if isUniversal{ return true }

    // Trivial if `self` is empty.
    if isEmpty { return positional.isEmpty && named.isEmpty }

    // Otherwise, we have to match each given argument with a pattern.
    var remainingPositional = positional[...]
    var matchedLabels: [String] = []
    var e = environment

    for pattern in patterns {
      switch pattern {
      case .positional(let binding):
        // Consume one positional argument.
        guard let value = remainingPositional.popFirst() else { return false }

        // If there's a binding, assign it or make sure its value matches.
        if let b = binding {
          if let m = e[b] {
            if m != value { return false }
          } else {
            e[b] = value
          }
        }

      case .positionalLiteral(let expected):
        // Consume one positional argument, which must be equal to the literal.
        guard let value = remainingPositional.popFirst(), value == expected else { return false }

      case .positionalVariadic(let binding):
        // If there's a binding, assign it or make sure its value matches.
        if let b = binding {
          // Gather the remaining positional arguments.
          let vs = Array(remainingPositional)

          // Assign or check for a match.
          if let m = e[b] {
            if m != .array(vs) { return false }
          } else {
            e[b] = .array(vs)
          }
        }

        // Mark all remaining positional arguments as having been matched.
        remainingPositional.removeAll()

      case .named(let label, let binding):
        // Consume a named argument with the specified label.
        guard let value = named[label], !matchedLabels.contains(label) else { return false }
        matchedLabels.append(label)

        // If there's a binding, assign it or make sure its value matches.
        if let b = binding {
          if let m = e[b] {
            if m != value { return false }
          } else {
            e[b] = value
          }
        }

      case .namedLiteral(let label, let expected):
        // Consume a named argument with the specified label, which must be equal to the literal.
        guard let value = named[label], !matchedLabels.contains(label), value == expected else {
          return false
        }
        matchedLabels.append(label)

      case .namedVariadic(let binding):
        // If there's a binding, assign it or make sure its value matches.
        if let b = binding {
          // Gather the remaining named arguments, making them as having been matched.
          var vs = SortedDictionary<String, Value>()
          for (k, v) in named where !matchedLabels.contains(k) {
            vs[k] = v
            matchedLabels.append(k)
          }

          // Assign or check for a match.
          if let m = e[b] {
            if m != .table(vs) { return false }
          } else {
            e[b] = .table(vs)
          }
        } else {
          // Mark all remaining positional arguments as having been matched.
          for k in named.keys where !matchedLabels.contains(k) {
            matchedLabels.append(k)
          }
        }

      case .universal:
        // Universal patterns should have been matched earler.
        fatalError("unreachable")
      }
    }

    // Did we match everything?
    if remainingPositional.isEmpty && matchedLabels.count == named.count {
      swap(&e, &environment)
      return true
    } else {
      return false
    }
  }

}

extension ArgumentPatternList: CustomStringConvertible {

  public var description: String {
    patterns.map(String.init(describing:)).joined(separator: ", ")
  }

}
