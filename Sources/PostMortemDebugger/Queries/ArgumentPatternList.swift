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
  ///
  /// Positional patterns match positional arguments in order, a variadic positional pattern
  /// matching any number of them. Named patterns match named arguments regardless of order, a
  /// variadic named pattern matching those that other named patterns don't.
  public func matches(
    _ positional: [Value], _ named: SortedDictionary<String, Value>,
    in environment: inout [String: Value]
  ) -> Bool {
    // Trivial if `self` is the universal pattern.
    if isUniversal { return true }

    var e = environment
    let p = patterns.filter(\.isPositional)
    if !Self.matches(p[...], positional[...], in: &e) { return false }
    if !Self.matches(patterns.filter({ (q) in !q.isPositional }), named, in: &e) { return false }
    swap(&e, &environment)
    return true
  }

  /// Returns `true` iff `patterns`, which are positional, match `arguments` in order, unifying
  /// variables in `environment`, which is left unchanged if they don't.
  private static func matches(
    _ patterns: ArraySlice<ArgumentPattern>, _ arguments: ArraySlice<Value>,
    in environment: inout [String: Value]
  ) -> Bool {
    guard let p = patterns.first else { return arguments.isEmpty }
    let rest = patterns.dropFirst()

    // The number of arguments that `p` can match, from the largest.
    let counts: [Int]
    switch p {
    case .positional, .positionalLiteral:
      counts = arguments.isEmpty ? [] : [1]
    case .positionalVariadic:
      let required = rest.count(where: { (q) in
        if case .positionalVariadic = q { false } else { true }
      })
      counts = arguments.count >= required ? Array((0 ... arguments.count - required).reversed()) : []
    default:
      fatalError("unreachable")
    }

    for n in counts {
      var e = environment
      let head = arguments.prefix(n)
      let matched: Bool =
        switch p {
        case .positional(let b): unify(b, head.first!, in: &e)
        case .positionalLiteral(let v): head.first!.isEqual(to: v)
        case .positionalVariadic(let b): unify(b, .array(Array(head)), in: &e)
        default: false
        }
      if matched && matches(rest, arguments.dropFirst(n), in: &e) {
        swap(&e, &environment)
        return true
      }
    }
    return false
  }

  /// Returns `true` iff `patterns`, which are named, match `arguments`, unifying variables in
  /// `environment`.
  private static func matches(
    _ patterns: [ArgumentPattern], _ arguments: SortedDictionary<String, Value>,
    in environment: inout [String: Value]
  ) -> Bool {
    var matchedLabels: Set<String> = []

    // Match the named arguments that have patterns of their own.
    for p in patterns {
      switch p {
      case .named(let label, let binding):
        guard let value = arguments[label], matchedLabels.insert(label).inserted,
          unify(binding, value, in: &environment)
        else { return false }
      case .namedLiteral(let label, let expected):
        guard let value = arguments[label], matchedLabels.insert(label).inserted,
          value.isEqual(to: expected)
        else { return false }
      default:
        continue
      }
    }

    // Match the others with variadic patterns, the first one taking them all.
    for case .namedVariadic(let binding) in patterns {
      var vs = SortedDictionary<String, Value>()
      for (k, v) in arguments where matchedLabels.insert(k).inserted {
        vs[k] = v
      }
      if !unify(binding, .table(vs), in: &environment) { return false }
    }

    return matchedLabels.count == arguments.count
  }

  /// Returns `true` iff `binding` is `nil`, unbound in `environment`, or bound to `value`, binding
  /// it to `value` in the second case.
  private static func unify(
    _ binding: String?, _ value: Value, in environment: inout [String: Value]
  ) -> Bool {
    guard let b = binding else { return true }
    if let m = environment[b] { return m.isEqual(to: value) }
    environment[b] = value
    return true
  }

}

extension ArgumentPatternList: CustomStringConvertible {

  public var description: String {
    patterns.map(String.init(describing:)).joined(separator: ", ")
  }

}
