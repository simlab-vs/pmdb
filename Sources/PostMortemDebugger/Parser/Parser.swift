import Foundation

/// The parsing of a command.
public struct Parser {

  /// The tokens in the input.
  private var tokens: Lexer

  /// The position immediately after the last consumed token.
  public private(set) var position: String.Index

  /// The next token to consume, if already extracted from the source.
  private var lookahead: Token? = nil

  /// The non-fatal diagnostics that have been collected so far.
  public private(set) var diagnostics: [Diagnostic] = []

  /// Creates a new instance parsing `source`.
  public init(_ source: String) {
    self.tokens = .init(tokenizing: source)
    self.position = source.startIndex
  }

  /// Returns the characters not consumed by the parser.
  public mutating func remainder() -> Substring {
    if let p = peek() {
      return tokens.source[p.site.lowerBound...]
    } else {
      return tokens.source[tokens.source.endIndex...]
    }
  }

  /// Parses a command.
  public mutating func parseCommand() throws -> Command {
    let head = try peek() ?? expected("command")
    switch head.tag {
    case .exit:
      return try parseExit()
    case .load:
      return try parseLoad()
    case .select:
      return try parseSelect()
    case .show:
      return try parseShow()
    default:
      throw Diagnostic(.error, "unknown command '\(text(head))'", at: head.site)
    }
  }

  /// Parses an exit command.
  private mutating func parseExit() throws -> Command {
    _ = try take(.exit) ?? expected("'exit'")
    return .exit
  }

  /// Parses a load command.
  private mutating func parseLoad() throws -> Command {
    _ = try take(.load) ?? expected("'load'")

    // Parse a URL from the raw characters.
    let raw = tokens.source[tokens.position...].drop(while: \.isWhitespace)
    let end = raw.firstIndex(where: \.isWhitespace) ?? raw.endIndex
    let url = URL(filePath: .init(raw[..<end]))
    tokens.advance(to: end)

    // Parse a name, if any.
    if take(contextual: "as") != nil {
      let n = try take(.variable) ?? expected("variable")
      return .load(url, name: text(n))
    } else {
      return .load(url, name: nil)
    }
  }

  /// Parses a select command.
  private mutating func parseSelect() throws -> Command {
    try .select(parseQuery())
  }

  /// Parses a query.
  private mutating func parseQuery() throws -> Query {
    _ = try take(.select) ?? expected("'select'")

    // There must be at least one identifier.
    let patternStart = nextTokenStart()
    let identifier = try parseIdentifierPattern()

    // If the next token is a left parenthesis, then we're parsing a call pattern.
    if take(.leftParenthesis) != nil {
      let xs = try parseArgumentPatternList()
      _ = try take(.rightParenthesis) ?? expected("')'")

      // Warn against innefficient patterns.
      if (xs.patterns != [.universal]) && xs.isEquivalentToUniversal {
        let w = Diagnostic(
          .warning, "'\(identifier)(\(xs))' is better expressed as '\(identifier)(...)'",
          at: span(from: patternStart))
        diagnostics.append(w)
      }

      // Is there a pattern for the result?
      let result = try take(operator: "->").map({ (_) in try parseResultPattern() })

      let (source, filter) = try parseQueryClauses()
      return .call(identifier, xs, result: result, from: source, where: filter)
    }

    // Otherwise, expect we're parsing identifiers in snapshots.
    else {
      let (source, filter) = try parseQueryClauses()
      return .snap(identifier, from: source, where: filter)
    }
  }

  /// Parses the from and/or where clause of a query, if present.
  private mutating func parseQueryClauses() throws -> (Query.FromClause, Expression?) {
    try (parseOptionalFromClause() ?? .query(.all), parseOptionalWhereClause())
  }

  /// Parses a from clause iff the next token is a `from` keyword.
  private mutating func parseOptionalFromClause() throws -> Query.FromClause? {
    if take(contextual: "from") == nil { return nil }

    if let n = take(.variable) {
      return .variable(text(n))
    } else {
      return try .query(parseQuery())
    }
  }

  /// Parses a where clause iff the next token is `where` keyword.
  private mutating func parseOptionalWhereClause() throws -> Expression? {
    if take(contextual: "where") != nil {
      return try parseExpression()
    } else {
      return nil
    }
  }

  /// Parses a show command.
  private mutating func parseShow() throws -> Command {
    _ = try take(.show) ?? expected("'show'")

    if let n = take(.variable) {
      return .show(text(n))
    } else if take(contextual: "variables") != nil {
      return .showConvenienceVariables
    } else {
      throw expected("variable")
    }
  }

  /// Parses an identifier pattern.
  private mutating func parseIdentifierPattern() throws -> IdentifierPattern {
    // Is the pattern a simple name?
    if let n = take(.name) {
      return .exactly(.init(tokens.source[n.site]))
    }

    // Is the pattern a regex?
    if let n = take(.regex) {
      return .regex(.init(text(n)))
    }

    // Is the pattern a wildcard?
    if take(.underscore) != nil {
      return .wildcard
    }

    // Out of luck.
    throw expected("identifier")
  }

  /// Parses a comma-separated list of argument patterns.
  private mutating func parseArgumentPatternList() throws -> ArgumentPatternList {
    // Is tha pattern universal?
    if take(.ellipsis) != nil {
      return .init([.universal])
    }

    // Otherwise, parse a list of patterns.
    let (xs, _) = try commaSeparated(until: Token.hasTag(.rightParenthesis)) { (me) in
      try me.parseArgumentPattern()
    }
    return .init(xs)
  }

  /// Parses an argument pattern.
  private mutating func parseArgumentPattern() throws -> ArgumentPattern {
    if let n = take(.name) {
      if take(.assign) != nil {
        if let v = take(.name) {
          return .named(label: text(n), binding: text(v))
        } else if take(.underscore) != nil {
          return .named(label: text(n), binding: nil)
        } else {
          throw expected("identifier")
        }
      } else if take(affixed: "*") != nil {
        return .positionalVariadic(binding: text(n))
      } else if take(affixed: "**") != nil {
        return .namedVariadic(binding: text(n))
      } else {
        return .positional(binding: text(n))
      }
    } else if take(.underscore) != nil {
      return .positional(binding: nil)
    } else if take(operator: "*") != nil {
      return .positionalVariadic(binding: nil)
    } else if take(operator: "**") != nil {
      return .namedVariadic(binding: nil)
    } else {
      throw expected("identifier")
    }
  }

  /// Parses the pattern matching the result of a call, which is a positional argument pattern.
  private mutating func parseResultPattern() throws -> ArgumentPattern {
    if let n = take(.name) {
      return .positional(binding: text(n))
    } else if take(.underscore) != nil {
      return .positional(binding: nil)
    } else {
      throw expected("result pattern")
    }
  }

  /// Parses a regular expression.
  private mutating func parseRegex() throws -> Regex<AnyRegexOutput> {
    let literal = try take(.regex) ?? expected("regex literal")
    let pattern = tokens.source[literal.site].dropFirst().dropLast()
    return try Regex<AnyRegexOutput>(.init(pattern))
  }

  /// Parses an expression.
  public mutating func parseExpression() throws -> Expression {
    try parseInfixExpression()
  }

  /// Parses a comma-separated list of labeled expressions.
  private mutating func parseExpressionList(
    until rightDelimiter: Token.Tag
  ) throws -> ([Expression], lastComma: Token?) {
    try commaSeparated(until: Token.hasTag(rightDelimiter)) { (me) in
      try me.parseExpression()
    }
  }

  /// Parses the root of infix expression whose operator binds at least as tightly as `p`.
  private mutating func parseInfixExpression(
    minimumPrecedence p: PrecedenceGroup = .disjunction
  ) throws -> Expression {
    let s = nextTokenStart()
    var l = try parsePrefixExpression()

    // Can we parse an operator with enough precedence?
    while p < .max, let (o, q) = try parseOptionalInfixOperator(notTighterThan: p) {
      let r = try parseInfixExpression(minimumPrecedence: q.next)
      let f = Expression(syntax: .identifier(text(o)), site: o.site)
      l = .init(syntax: .apply(.init(callee: f, arguments: [l, r])), site: span(from: s))
    }

    // Done.
    return l
  }

  /// Parses an expression optionally prefixed by an operator.
  private mutating func parsePrefixExpression() throws -> Expression {
    guard let o = take(.operator) else { return try parseCompoundExpression() }
    let e = try parseCompoundExpression()
    let f = Expression(syntax: .identifier(text(o)), site: o.site)
    return .init(syntax: .apply(.init(callee: f, arguments: [e])), site: span(from: o))
  }

  /// Parses an expression made of one or more components.
  private mutating func parseCompoundExpression() throws -> Expression {
    var head = try parsePrimaryExpression()
    while true {
      if var next = try appendArguments(to: head) {
        swap(&head, &next)
      } else if var next = try appendElementSelection(to: head) {
        swap(&head, &next)
      } else if var next = try appendPropertySelection(to: head) {
        swap(&head, &next)
      } else if var next = try appendLambda(to: head) {
        swap(&head, &next)
      } else {
        break
      }
    }
    return head
  }

  /// If the next token is a left parenthesis, parses an argument list and returns a call applying
  /// `head`. Otherwise, returns `nil`.
  private mutating func appendArguments(to head: Expression) throws -> Expression? {
    if !next(is: .leftParenthesis) { return nil }
    let (xs, _) = try inParentheses{ (me) in
      try me.parseExpressionList(until: .rightParenthesis)
    }
    let s = span(from: head.site.lowerBound)
    return .init(syntax: .apply(.init(callee: head, arguments: xs)), site: s)
  }

  /// If the next token is a left bracket, parses an array index and returns a the selection of an
  /// element of `head`. Otherwise, returns `nil`.
  private mutating func appendElementSelection(to head: Expression) throws -> Expression? {
    if !next(is: .leftBracket) { return nil }
    let i = try inBrackets({ (me) in try me.parseExpression() })
    let s = span(from: head.site.lowerBound)
    return .init(syntax: .element(.init(array: head, index: i)), site: s)
  }

  /// If the next token is a dot, parses an identifier and returns a the selection of a property of
  /// `head`. Otherwise, returns `nil`.
  private mutating func appendPropertySelection(to head: Expression) throws -> Expression? {
    if take(.dot) == nil { return nil }
    let n = try take(.name) ?? expected("identifier")
    let x = Parsed(text(n), at: n.site)
    let s = span(from: head.site.lowerBound)
    return .init(syntax: .property(.init(table: head, name: x)), site: s)
  }

  /// If the next token is an arrow and `head` is a simple identifier, parses an expression and
  /// returns a ambda, reinterpreting `head` as its parameter. Otherwise, returns `nil`.
  private mutating func appendLambda(to head: Expression) throws -> Expression? {
    if case .identifier(let p) = head.syntax, take(.arrow) != nil {
      let s = span(from: head.site.lowerBound)
      let x = Parsed(p, at: head.site)
      let b = try parseExpression()
      return .init(syntax: .lambda(.init(parameter: x, body: b)), site: s)
    } else {
      return nil
    }
  }

  /// Parses a simple expression.
  private mutating func parsePrimaryExpression() throws -> Expression {
    switch peek()?.tag {
    case .true, .false:
      return try parseBooleanLiteral()
    case .noneLiteral:
      let head = take()!
      return .init(syntax: .noneLiteral, site: head.site)
    case .integerLiteral:
      return try parseIntegerLiteral()
    case .floatingPointLiteral:
      return try parseFloatingPointLiteral()
    case .stringLiteral:
      return try parseStringLiteral()
    case .name:
      return try parseIdentifier()
    case .if:
      return try parseConditional()
    case .leftParenthesis:
      return try parseParenthesizedExpression()
    default:
      throw expected("expression")
    }
  }

  /// Parses a reference to the standard library.
  private mutating func parseLibraryReference() throws -> Expression {
    let head = try take(.pmdb) ?? expected("pmdb")
    return .init(syntax: .pmdb, site: head.site)
  }

  /// Parses a Boolean literal.
  private mutating func parseBooleanLiteral() throws -> Expression {
    let head = try (take(.true) ?? take(.false)) ?? expected("Boolean literal")
    return .init(syntax: .boolean(tokens.source[head.site] == "true"), site: head.site)
  }

  /// Parses an integer literal.
  private mutating func parseIntegerLiteral() throws -> Expression {
    let head = try take(.integerLiteral) ?? expected("integer literal")
    return .init(syntax: .integer(text(head)), site: head.site)
  }

  /// Parses a floating-point literal.
  private mutating func parseFloatingPointLiteral() throws -> Expression {
    let head = try take(.floatingPointLiteral) ?? expected("floating-point literal")
    return .init(syntax: .float(text(head)), site: head.site)
  }

  /// Parses a string literal.
  private mutating func parseStringLiteral() throws -> Expression {
    let head = try take(.stringLiteral) ?? expected("string literal")
    let contents = tokens.source[head.site].dropFirst().dropLast()

    var v = ""
    var escaped = false
    for c in contents {
      if escaped {
        switch c {
        case "n": v.append("\n")
        case "t": v.append("\t")
        case "\\", "\"": v.append(c)
        default:
          throw Diagnostic(.error, "invalid escape sequence '\\\(c)'", at: head.site)
        }
        escaped = false
      } else if c == "\\" {
        escaped = true
      } else {
        v.append(c)
      }
    }
    return .init(syntax: .string(v), site: head.site)
  }

  /// Parses a simple identifier.
  private mutating func parseIdentifier() throws -> Expression {
    let n = try take(.name) ?? expected("identifer")
    return .init(syntax: .identifier(text(n)), site: n.site)
  }

  /// Parses a conditional expression.
  private mutating func parseConditional() throws -> Expression {
    let head = try take(.if) ?? expected("'if'")
    let a = try parseExpression()
    _ = try take(.then) ?? expected("'then'")
    let b = try parseExpression()
    _ = try take(.else) ?? expected("'else'")
    let c = try parseExpression()

    return .init(
      syntax: .conditional(.init(condition: a, success: b, failure: c)),
      site: span(from: head))
  }

  /// Parses an expression enclosed in parentheses.
  private mutating func parseParenthesizedExpression() throws -> Expression {
    try inParentheses({ (me) in try me.parseExpression() })
  }

  /// Parses an array index.
  private mutating func parseArrayIndex() throws -> Parsed<Int> {
    let n = try take(.integerLiteral) ?? expected("array index")
    let i = try Int(text(n)) ?? illegalArrayIndex(n)
    return .init(i, at: n.site)
  }

  /// Parses an infix operator iff it binds less than or as tightly as `p`.
  private mutating func parseOptionalInfixOperator(
    notTighterThan p: PrecedenceGroup
  ) throws -> (Token, PrecedenceGroup)? {
    if !next(is: .operator) { return nil }

    var backup = self
    let o = take(.operator)!
    let q = PrecedenceGroup(containing: tokens.source[o.site])
    if (p < q) || (p == q) {
      return (o, q)
    } else {
      swap(&self, &backup)
      return nil
    }
  }

  /// Parses a list of instances of `T` separated by colons.
  private mutating func commaSeparated<T>(
    until isRightDelimiter: (Token) -> Bool, _ parse: (inout Self) throws -> T
  ) throws -> ([T], lastComma: Token?) {
    var xs: [T] = []
    var lastComma: Token? = nil
    while let head = peek(), !isRightDelimiter(head) {
      if !xs.isEmpty && (lastComma == nil) {
        throw expected("','")
      }
      try xs.append(parse(&self))
      if let c = take(.comma) {
        lastComma = c
      }
    }
    return (xs, lastComma)
  }

  /// Parses an instance of `T` enclosed in `delimiters`.
  private mutating func between<T>(
    _ delimiters: (left: Token.Tag, right: Token.Tag),
    _ parse: (inout Self) throws -> T
  ) throws -> T {
    _ = try take(delimiters.left) ?? expected(delimiters.left.errorDescription)
    let contents = try parse(&self)
    if take(delimiters.right) == nil {
      throw expected(delimiters.right.errorDescription)
    }
    return contents
  }

  /// Parses an instance of `T` enclosed in brackets.
  private mutating func inBrackets<T>(_ parse: (inout Self) throws -> T) throws -> T {
    try between((.leftBracket, .rightBracket), parse)
  }

  /// Parses an instance of `T` enclosed in parentheses.
  private mutating func inParentheses<T>(_ parse: (inout Self) throws -> T) throws -> T {
    try between((.leftParenthesis, .rightParenthesis), parse)
  }

  /// Returns `true` iff there is a whitespace before the next token.
  private mutating func whitespaceBeforeNextToken() -> Bool {
    if let n = peek() {
      return tokens.source[position ..< n.site.lowerBound].contains(where: \.isWhitespace)
    } else {
      return false
    }
  }

  /// Returns the start position of the next token or the current position if the stream is empty.
  private mutating func nextTokenStart() -> String.Index {
    peek()?.site.lowerBound ?? position
  }

  /// Returns a source span from `s` to the current position.
  private func span(from s: String.Index) -> Range<String.Index> {
    s ..< position
  }

  /// Returns a source span from the first position of `t` to the current position.
  private func span(from t: Token) -> Range<String.Index> {
    t.site.lowerBound ..< position
  }

  /// Returns `true` iff the next token has tag `k`, without consuming that token.
  private mutating func next(is k: Token.Tag) -> Bool {
    peek()?.tag == k
  }

  /// Returns `true` iff the next token satisfies `predicate`, without consuming that token.
  private mutating func next(satisfies predicate: (Token) -> Bool) -> Bool {
    peek().map(predicate) ?? false
  }

  /// Returns the next token without consuming it.
  private mutating func peek() -> Token? {
    if lookahead == nil { lookahead = tokens.next() }
    return lookahead
  }

  /// Consumes and returns the next token.
  private mutating func take() -> Token? {
    let next = lookahead.take() ?? tokens.next()
    position = next?.site.upperBound ?? tokens.source.endIndex
    return next
  }

  /// Consumes and returns the next token iff it has tag `k`.
  private mutating func take(_ k: Token.Tag) -> Token? {
    next(is: k) ? take() : nil
  }

  /// Consumes and returns the next token iff it satisifies `predicate`.
  private mutating func take(if predicate: (Token) -> Bool) -> Token? {
    next(satisfies: predicate) ? take() : nil
  }

  /// Consumes and returns the next token iff it is a contextual keyword with the given value.
  private mutating func take(contextual s: String) -> Token? {
    take(if: { [tokens] (t) in (t.tag == .name) && (tokens.source[t.site] == s) })
  }

  /// Consumes and returns the next token iff it is an operator with the given value.
  private mutating func take(operator s: String) -> Token? {
    take(if: { [tokens] (t) in (t.tag == .operator) && (tokens.source[t.site] == s) })
  }

  /// Consumes and returns the next token iff it is an operator equal to `s` and there are no
  /// leading whitespace from the current position to its start.
  private mutating func take(affixed s: String) -> Token? {
    (next(is: .operator) && !whitespaceBeforeNextToken()) ? take(operator: s) : nil
  }

  /// Consumes and returns characters until one does not satisfy `isIncluded`.
  private mutating func takeCharacters(while isIncluded: (Character) -> Bool) -> Substring {
    let start = tokens.position
    lookahead = nil
    position = tokens.source.firstIndex(where: { (c) in !isIncluded(c) }) ?? tokens.source.endIndex
    return tokens.source[start ..< position]
  }

  /// Returns the characters composing `token`.
  private func text(_ token: Token) -> String {
    .init(tokens.source[token.site])
  }

  /// Returns a parse error reporting that `s` was expected at the current position.
  private func expected(_ s: String) -> Diagnostic {
    expected(s, at: position ..< position)
  }

  /// Returns a parse error reporting that `s` was expected at `site`.
  private func expected(_ s: String, at site: Range<String.Index>) -> Diagnostic {
    .init(.error, "expected \(s)", at: site)
  }

  /// Returns a parse error reporting a failure to parse an array index.
  private func illegalArrayIndex(_ i: Token) -> Diagnostic {
    .init(.error, "cannot parse '\(text(i))' as an index", at: i.site)
  }

}

extension Token.Tag {

  /// Returns a description of `self` for error reporting.
  fileprivate var errorDescription: String {
    switch self {
    case .leftBrace: "'{'"
    case .rightBrace: "'}'"
    case .leftBracket: "'['"
    case .rightBracket: "']'"
    case .leftParenthesis: "'('"
    case .rightParenthesis: "')'"
    default: "\(self)"
    }
  }

}
