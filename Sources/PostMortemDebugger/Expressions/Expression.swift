/// The expression of a value part of a query filter.
public struct Expression: Hashable, Sendable {

  /// The site from which the expression was parsed.
  public let site: Range<String.Index>

  /// The syntax of the expression.
  public let syntax: Syntax

  /// Creates an instance with the given properties.
  public init(syntax: Syntax, site: Range<String.Index>) {
    self.syntax = syntax
    self.site = site
  }

}

extension Expression {

  /// An abstract syntax tree.
  public indirect enum Syntax: Hashable, Sendable {

    /// A reference to the standard library.
    case pmdb

    /// The literal denoting the absence of a value.
    case noneLiteral

    /// A Boolean literal.
    case boolean(Bool)

    /// An integer literal.
    case integer(String)

    /// A floating-point literal.
    case float(String)

    /// A string literal.
    case string(String)

    /// An identifier.
    case identifier(String)

    /// A conditional expression.
    case conditional(Conditional)

    /// A function call.
    case apply(Apply)

    /// A closure.
    case lambda(Lambda)

    /// An element selection.
    case element(Element)

    /// A property selection.
    case property(Property)

  }

  /// A conditional expression.
  public struct Conditional: Hashable, Sendable {

    /// The condition being tested.
    public let condition: Expression

    /// The expression evaluated iff the condition holds.
    public let success: Expression

    /// The expression evaluated iff the condition does not hold.
    public let failure: Expression

    /// Creates an instance with the given properties.
    public init(condition: Expression, success: Expression, failure: Expression) {
      self.condition = condition
      self.success = success
      self.failure = failure
    }

  }

  /// The application of a function.
  public struct Apply: Hashable, Sendable {

    /// The callee and its arguments.
    private let children: [Expression]

    /// Creates an instance with the given properties.
    public init<T: Sequence<Expression>>(callee: Expression, arguments: T) {
      self.children = .init(head: callee, tail: arguments)
    }

    /// The expression of the function being called.
    public var callee: Expression { children[0] }

    /// The arguments of the call.
    public var arguments: ArraySlice<Expression> { children[1...] }

  }

  /// A term abstraction.
  public struct Lambda: Hashable, Sendable {

    /// The parameter of the abstraction.
    public let parameter: Parsed<String>

    /// The body of the abstraction.
    public let body: Expression

    /// Creates an instance with the given properties.
    public init(parameter: Parsed<String>, body: Expression) {
      self.parameter = parameter
      self.body = body
    }

  }

  /// The selection of an element in an array.
  public struct Element: Hashable, Sendable {

    /// The expression of the array containing the element being selected.
    public let array: Expression

    /// The index of the element.
    public let index: Expression

    /// Creates an instance with the given properties.
    public init(array: Expression, index: Expression) {
      self.array = array
      self.index = index
    }

  }

  /// The selection of a property in an table.
  public struct Property: Hashable, Sendable {

    /// The expression of the table containing the property being selected.
    public let table: Expression

    /// The name of the property.
    public let name: Parsed<String>

    /// Creates an instance with the given properties.
    public init(table: Expression, name: Parsed<String>) {
      self.table = table
      self.name = name
    }

  }

}

extension Expression: CustomStringConvertible {

  public var description: String {
    switch syntax {
    case .pmdb:
      return "pmdb"
    case .noneLiteral:
      return "none"
    case .boolean(let n):
      return n.description
    case .integer(let n):
      return n
    case .float(let n):
      return n
    case .string(let n):
      return n
    case .identifier(let n):
      return n
    case .conditional(let n):
      return n.description
    case .apply(let n):
      return n.description
    case .lambda(let n):
      return n.description
    case .element(let n):
      return n.description
    case .property(let n):
      return n.description
    }
  }

}

extension Expression.Conditional: CustomStringConvertible {

  public var description: String {
    "if \(condition) then \(success) else \(failure)"
  }

}

extension Expression.Apply: CustomStringConvertible {

  public var description: String {
    "\(callee)(\(arguments.map(String.init(describing:)).joined(separator: ", ")))"
  }

}

extension Expression.Lambda: CustomStringConvertible {

  public var description: String {
    "\\\(parameter) => \(body)"
  }

}

extension Expression.Element: CustomStringConvertible {

  public var description: String {
    "\(array)[\(index)]"
  }

}

extension Expression.Property: CustomStringConvertible {

  public var description: String {
    "\(table).\(name)"
  }

}
