extension Expression {

  /// Returns the value of `self` evaluated in the specified `environment`.
  public func evaluate(in environment: inout [String: Value]) throws -> Value {
    switch syntax {
    case .pmdb:
      fatalError("TODO")
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
    // Is the callee an infix or prefix operator?
    switch callee.syntax {
    case .identifier("<"):
      return try compareNumerically(in: &environment) { (r) in r < 0 }
    case .identifier("<="):
      return try compareNumerically(in: &environment) { (r) in r <= 0 }
    case .identifier(">"):
      return try compareNumerically(in: &environment) { (r) in r > 0 }
    case .identifier(">="):
      return try compareNumerically(in: &environment) { (r) in r >= 0 }
    case .identifier("=="):
      return try compareNumerically(in: &environment) { (r) in r == 0 }
    case .identifier("!="):
      return try compareNumerically(in: &environment) { (r) in r != 0 }
    case .identifier("+"):
      return try binary(in: &environment,) { (a, b) in a.add(b) }
    case .identifier("-"):
      return try binary(in: &environment,) { (a, b) in a.sub(b) }
    case .identifier("*"):
      return try binary(in: &environment,) { (a, b) in a.mul(b) }
    case .identifier("/"):
      return try binary(in: &environment,) { (a, b) in a.div(b) }
    default:
      throw Diagnostic.error("unsupported operation '\(callee)'", at: callee.site)
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
    return try combine(a, b) ?? Diagnostic.invalidBinaryOperation(callee, a, b)
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
    switch try table.evaluate(in: &environement) {
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
      return Int((lhs - rhs).within(-1 ... 1))
    case (.float(let lhs), .float(let rhs)):
      return if lhs == rhs { 0 } else if lhs < rhs { -1 } else { 1 }
    default:
      return nil
    }
  }

  /// Returns the sum of `self` and `other` iff that operation is defined.
  fileprivate func add(_ other: Value) -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return .integer(lhs + rhs)
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs + rhs)
    default:
      return nil
    }
  }

  /// Returns `other` subtraced from `self` iff that operation is defined.
  fileprivate func sub(_ other: Value) -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return .integer(lhs - rhs)
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs - rhs)
    default:
      return nil
    }
  }

  /// Returns `self` multiplied by `other` iff that operation is defined.
  fileprivate func mul(_ other: Value) -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return .integer(lhs * rhs)
    case (.float(let lhs), .float(let rhs)):
      return .float(lhs * rhs)
    default:
      return nil
    }
  }

  /// Returns `self` divided by `other` iff that operation is defined.
  fileprivate func div(_ other: Value) -> Value? {
    switch (self, other) {
    case (.integer(let lhs), .integer(let rhs)):
      return (rhs != 0) ? .integer(lhs / rhs) : nil
    case (.float(let lhs), .float(let rhs)):
      return (rhs != 0) ? .float(lhs / rhs) : nil
    default:
      return nil
    }
  }

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
