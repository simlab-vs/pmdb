extension Expression {

  /// Returns the value of `self` evaluated in the specified `environment`.
  public func evaluate(in environment: inout [String: Value]) throws -> Value {
    switch syntax {
    case .pmdb:
      fatalError("TODO")
    case .noneLiteral:
      return .null
    case .boolean(let v):
      return .init(v)
    case .integer(let v):
      return try .integer(Int64(v) ?? Diagnostic.invalidIntergerLiteral(v, at: site))
    case .float(let v):
      return try .float(Double(v) ?? Diagnostic.invalidIntergerLiteral(v, at: site))
    case .string(let v):
      return .string(v)
    case .identifier(let x):
      return try environment[x] ?? Diagnostic.undefined(x, at: site)
    case .conditional(let t):
      return try t.evaluate(in: &environment)
    case .apply(let t):
      return try t.evaluate(in: &environment)
    case .lambda(let t):
      return .lambda(t, environment)
    case .element(let t):
      return try t.evaluate(in: &environment)
    case .property(let t):
      return try t.evaluate(in: &environment)
    }
  }

}

extension Expression.Conditional {

  /// Returns the value of `self` evaluated in the specified `environment`.
  fileprivate func evaluate(in environement: inout [String: Value]) throws -> Value {
    if try condition.evaluate(in: &environement).isTruthy {
      return try success.evaluate(in: &environement)
    } else {
      return try failure.evaluate(in: &environement)
    }
  }

}

extension Expression.Apply {

  /// Returns the value of `self` evaluated in the specified `environment`.
  fileprivate func evaluate(in environment: inout [String: Value]) throws -> Value {
    // Is the callee a prefix operator?
    if arguments.count == 1 {
      switch callee.syntax {
      case .identifier("!"):
        return try .init(!arguments.first!.evaluate(in: &environment).isTruthy)
      case .identifier("-"):
        return try unary(in: &environment) { (a) in try a.negated() }
      case .identifier(let o) where o.first.map({ (c) in !c.isLetter && c != "_" }) ?? false:
        throw Diagnostic.error("unsupported prefix operator '\(o)'", at: callee.site)
      default:
        break
      }
    }

    // Is the callee an infix operator?
    switch callee.syntax {
    case .identifier("&&"):
      return try logical(in: &environment, shortCircuitingOn: false)
    case .identifier("||"):
      return try logical(in: &environment, shortCircuitingOn: true)
    case .identifier("<"):
      return try compareNumerically(in: &environment) { (r) in r < 0 }
    case .identifier("<="):
      return try compareNumerically(in: &environment) { (r) in r <= 0 }
    case .identifier(">"):
      return try compareNumerically(in: &environment) { (r) in r > 0 }
    case .identifier(">="):
      return try compareNumerically(in: &environment) { (r) in r >= 0 }
    case .identifier("=="):
      return try compareForEquality(in: &environment) { (r) in r }
    case .identifier("!="):
      return try compareForEquality(in: &environment) { (r) in !r }
    case .identifier("+"):
      return try binary(in: &environment,) { (a, b) in try a.add(b) }
    case .identifier("-"):
      return try binary(in: &environment,) { (a, b) in try a.sub(b) }
    case .identifier("*"):
      return try binary(in: &environment,) { (a, b) in try a.mul(b) }
    case .identifier("/"):
      return try binary(in: &environment,) { (a, b) in try a.div(b) }
    case .identifier("&"):
      return try binary(in: &environment,) { (a, b) in a.bitwise(b, &) }
    case .identifier("^"):
      return try binary(in: &environment,) { (a, b) in a.bitwise(b, ^) }
    case .identifier("|"):
      return try binary(in: &environment,) { (a, b) in a.bitwise(b, |) }
    case .identifier(let o) where o.first.map({ (c) in !c.isLetter && c != "_" }) ?? false:
      throw Diagnostic.error("unsupported operation '\(callee)'", at: callee.site)
    default:
      break
    }

    // Is the callee a method of an array or a table? Tables can't contain lambdas, so the
    // application of one of their properties can only denote a method.
    let f: Value
    if case .property(let p) = callee.syntax {
      let receiver = try p.table.evaluate(in: &environment)
      switch receiver {
      case .array(let xs):
        return try apply(method: p.name, of: xs, in: &environment)
      case .table(let t) where p.name.value == "len":
        return try length(of: t)
      default:
        break
      }
      f = try p.select(in: receiver)
    } else {
      f = try callee.evaluate(in: &environment)
    }

    // Otherwise, the callee must be a lambda.
    if arguments.count != 1 {
      throw Diagnostic.invalidArgumentCount(expected: 1, found: arguments.count, at: callee.site)
    }
    return try Expression.apply(f, to: arguments.first!.evaluate(in: &environment), at: callee.site)
  }

  /// Evaluates `self` as the application of the method `m` of the array `xs`.
  private func apply(
    method m: Parsed<String>, of xs: [Value], in environment: inout [String: Value]
  ) throws -> Value {
    switch m.value {
    case "all":
      let p = try predicate(in: &environment)
      return try .init(xs.allSatisfy(p))
    case "any":
      let p = try predicate(in: &environment)
      return try .init(xs.contains(where: p))
    case "count":
      let p = try predicate(in: &environment)
      return try .integer(Int64(xs.count(where: p)))
    case "len":
      return try length(of: xs)
    default:
      throw Diagnostic.error("value of type 'array' has no method '\(m.value)'", at: m.site)
    }
  }

  /// Evaluates `self` as the application of the method `len` of `c`.
  private func length<T: Collection>(of c: T) throws -> Value {
    if !arguments.isEmpty {
      throw Diagnostic.invalidArgumentCount(expected: 0, found: arguments.count, at: callee.site)
    }
    return .integer(Int64(c.count))
  }

  /// Returns a function that applies the lambda passed as the only argument of `self` to a value
  /// and returns whether the result is truthy.
  private func predicate(
    in environment: inout [String: Value]
  ) throws -> (Value) throws -> Bool {
    if arguments.count != 1 {
      throw Diagnostic.invalidArgumentCount(expected: 1, found: arguments.count, at: callee.site)
    }
    let f = try arguments.first!.evaluate(in: &environment)
    return { [site = callee.site] (x) in try Expression.apply(f, to: x, at: site).isTruthy }
  }

  /// Evaluates `self` as a unary operation on an operand evaluated in `environment`, computing its
  /// result with `transform`.
  private func unary(
    in environment: inout [String: Value],
    computingResultWith transform: (Value) throws -> Value?
  ) throws -> Value {
    let a = try arguments.first!.evaluate(in: &environment)
    do {
      return try transform(a)
        ?? Diagnostic.error("cannot apply \(callee) on value of type '\(a.type)'", at: callee.site)
    } catch let e as ArithmeticFailure {
      throw Diagnostic.error("\(e.reason) in '\(callee)'", at: callee.site)
    }
  }

  /// Evaluates `self` as a logical conjunction or disjunction of operands evaluated in
  /// `environment`, evaluating its right operand iff the truthiness of its left operand isn't
  /// `shortCircuit`.
  private func logical(
    in environment: inout [String: Value], shortCircuitingOn shortCircuit: Bool
  ) throws -> Value {
    if arguments.count != 2 {
      throw Diagnostic.invalidArgumentCount(expected: 2, found: arguments.count, at: callee.site)
    }

    if try arguments.first!.evaluate(in: &environment).isTruthy == shortCircuit {
      return .init(shortCircuit)
    } else {
      return try .init(arguments.last!.evaluate(in: &environment).isTruthy)
    }
  }

  /// Evaluates `self` as a binary operation between operands evaluated in `environment`, combining
  /// their values with `combine`.
  private func binary(
    in environment: inout [String: Value],
    computingResultWith combine: (Value, Value) throws -> Value?
  ) throws -> Value {
    if arguments.count != 2 {
      throw Diagnostic.invalidArgumentCount(expected: 2, found: arguments.count, at: callee.site)
    }

    let a = try arguments.first!.evaluate(in: &environment)
    let b = try arguments.last!.evaluate(in: &environment)
    do {
      return try combine(a, b) ?? Diagnostic.invalidBinaryOperation(callee, a, b)
    } catch let e as ArithmeticFailure {
      throw Diagnostic.error("\(e.reason) in '\(callee)'", at: callee.site)
    }
  }

  /// Evaluates `self` as an equality test between operands evaluated in `environment`, using
  /// `transform` to convert the result of the test to a Boolean.
  ///
  /// Numbers are compared numerically. Other values are equal iff they have the same type and
  /// contents, except that `none` can be compared with any value.
  private func compareForEquality(
    in environment: inout [String: Value],
    transformingResultWith transform: (Bool) -> Bool
  ) throws -> Value {
    try binary(in: &environment) { (a, b) in
      if let result = a.compareNumerically(to: b) {
        return .init(transform(result == 0))
      }
      switch (a, b) {
      case (.null, _), (_, .null), (.string, .string), (.array, .array), (.table, .table), (.function, .function),
        (.object, .object):
        return .init(transform(a == b))
      default:
        throw Diagnostic.invalidBinaryOperation(callee, a, b)
      }
    }
  }

  /// Evaluates `self` as a numeric comparison between operands evaluared in `environment`, using
  /// `transform` to convert the result of two-way comparisons to a Boolean.
  private func compareNumerically(
    in environment: inout [String: Value],
    transformingResultWith transform: (Int) -> Bool
  ) throws -> Value {
    try binary(in: &environment) { (a, b) in
      if let result = a.compareNumerically(to: b) {
        return .init(transform(result))
      } else {
        throw Diagnostic.invalidBinaryOperation(callee, a, b)
      }
    }
  }

}

extension Expression {

  /// Returns the result of applying `f` to `a`, reporting errors at `site` if `f` isn't a lambda.
  fileprivate static func apply(
    _ f: Value, to a: Value, at site: Range<String.Index>
  ) throws -> Value {
    guard case .lambda(let l, var environment) = f else {
      throw Diagnostic.error("value of type '\(f.type)' is not a lambda", at: site)
    }
    environment[l.parameter.value] = a
    return try l.body.evaluate(in: &environment)
  }

}

extension Expression.Element {

  /// Returns the value of `self` evaluated in the specified `environment`.
  fileprivate func evaluate(in environment: inout [String: Value]
  ) throws -> Value {
    switch try array.evaluate(in: &environment) {
    case .array(let t):
      switch try index.evaluate(in: &environment) {
      case .integer(let i) where UInt64(bitPattern: i) < t.count:
        return t[Int(i)]
      case .integer(let i):
        throw Diagnostic.outOfBounds(i, at: index.site)
      case let v:
        throw Diagnostic.invalidIndex(v, at: index.site)
      }
    case let v:
      throw Diagnostic.invalidElementSelection(on: v, at: index.site)
    }
  }

}

extension Expression.Property {

  /// Returns the value of `self` evaluated in the specified `environment`.
  fileprivate func evaluate(in environement: inout [String: Value]) throws -> Value {
    try select(in: table.evaluate(in: &environement))
  }

  /// Returns the value of the property of `receiver` selected by `self`.
  fileprivate func select(in receiver: Value) throws -> Value {
    switch receiver {
    case .table(let t):
      return try t[name.value] ?? Diagnostic.undefined(property: name)
    case let v:
      throw Diagnostic.invalidPropertySelection(on: v, at: name.site)
    }
  }

}

extension Value {

  /// Returns `-1`, `0`, `1`, or `nil` if `self` is respectively less than, equal to, greater than,
  /// or incomparable to `other`.
  fileprivate func compareNumerically(to other: Value) -> Int? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return if lhs == rhs { 0 } else if lhs < rhs { -1 } else { 1 }
    case (.float(let lhs), .float(let rhs)):
      return if lhs == rhs { 0 } else if lhs < rhs { -1 } else { 1 }
    default:
      return nil
    }
  }

  /// Returns the negation of `self` iff that operation is defined.
  fileprivate func negated() throws -> Value? {
    switch self {
    case .integer(let v):
      return try checked(Int64(0).subtractingReportingOverflow(v))
    case .float(let v):
      return .float(-v)
    default:
      return nil
    }
  }

  /// Returns the sum of `self` and `other` iff that operation is defined.
  fileprivate func add(_ other: Value) throws -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return try checked(lhs.addingReportingOverflow(rhs))
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs + rhs)
    default:
      return nil
    }
  }

  /// Returns `other` subtraced from `self` iff that operation is defined.
  fileprivate func sub(_ other: Value) throws -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return try checked(lhs.subtractingReportingOverflow(rhs))
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs - rhs)
    default:
      return nil
    }
  }

  /// Returns `self` multiplied by `other` iff that operation is defined.
  fileprivate func mul(_ other: Value) throws -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return try checked(lhs.multipliedReportingOverflow(by: rhs))
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs * rhs)
    default:
      return nil
    }
  }

  /// Returns `self` divided by `other` iff that operation is defined.
  fileprivate func div(_ other: Value) throws -> Value? {
    switch (self, other) {
    case (.integer, .integer(0)), (.float, .float(0)):
      throw ArithmeticFailure(reason: "division by zero")
    case (.integer(let lhs), .integer(let rhs)):
      return try checked(lhs.dividedReportingOverflow(by: rhs))
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs / rhs)
    default:
      return nil
    }
  }

  /// Returns `combine` applied on the bits of `self` and `other` iff both are integers.
  fileprivate func bitwise(_ other: Value, _ combine: (Int64, Int64) -> Int64) -> Value? {
    if case .integer(let lhs) = self, case .integer(let rhs) = other {
      return .integer(combine(lhs, rhs))
    } else {
      return nil
    }
  }

  /// Returns `r.partialValue` iff `r` did not overflow. Otherwise, throws.
  private func checked(_ r: (partialValue: Int64, overflow: Bool)) throws -> Value {
    if r.overflow { throw ArithmeticFailure(reason: "arithmetic overflow") }
    return .integer(r.partialValue)
  }

}

/// The failure of an arithmetic operation whose operands have valid types.
private struct ArithmeticFailure: Error {

  /// A description of the failure.
  let reason: String

}

extension Diagnostic {

  /// Returns an error reported at `site` and explained by `message`.
  fileprivate static func error(_ message: String, at site: Range<String.Index>) -> Diagnostic {
    .init(.error, message, at: site)
  }

  /// Returns an error diagnosing an undefined symbol.
  fileprivate static func undefined(_ x: String, at site: Range<String.Index>) -> Diagnostic {
    error("undefined symbol '\(x)'", at: site)
  }

  /// Returns an error diagnosing the selection of an undefined property.
  fileprivate static func undefined(property x: Parsed<String>) -> Diagnostic {
    error("undefined property '\(x.value)'", at: x.site)
  }

  /// Returns an error diagnosing an invalid number of arguments in a function application.
  fileprivate static func invalidArgumentCount(
    expected: Int, found: Int, at site: Range<String.Index>
  ) -> Diagnostic {
    error("expected \(expected) argument(s), found \(found)", at: site)
  }

  /// Returns an error diagnosing a type error while appliying a binary operator.
  fileprivate static func invalidBinaryOperation(
    _ f: Expression, _ a: Value, _ b: Value
  ) -> Diagnostic {
    error("cannot apply \(f) on values of type '\(a.type)' and '\(b.type)'", at: f.site)
  }

  /// Returns an error diagnosing an invalid literal.
  fileprivate static func invalidIntergerLiteral(
    _ v: String, at site: Range<String.Index>
  ) -> Diagnostic {
    error("cannot parse '\(v)' as an integer literal", at: site)
  }

  /// Returns an error diagnosing an invalid literal.
  fileprivate static func invalidFloatingPointLiteral(
    _ v: String, at site: Range<String.Index>
  ) -> Diagnostic {
    error("cannot parse '\(v)' as a floating-point literal", at: site)
  }

  /// Returns an error diagnosing an invalid index type.
  fileprivate static func invalidIndex(_ v: Value, at site: Range<String.Index>) -> Diagnostic {
    error("cannot use value of type '\(v.type)' as an array index", at: site)
  }

  /// Returns an error diagnosing an element access on something other than a array.
  fileprivate static func invalidElementSelection(
    on v: Value, at site: Range<String.Index>
  ) -> Diagnostic {
    error("value of type '\(v.type)' is not an array", at: site)
  }

  /// Returns an error diagnosing a property selection on something other than a table.
  fileprivate static func invalidPropertySelection(
    on v: Value, at site: Range<String.Index>
  ) -> Diagnostic {
    error("value of type '\(v.type)' is not a table", at: site)
  }

  /// Returns an error diagnosing an array index that is out of bounds.
  fileprivate static func outOfBounds(_ i: Int64, at site: Range<String.Index>) -> Diagnostic {
    error("index '\(i)' is out of bounds", at: site)
  }

}
