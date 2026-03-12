/// The tokens of a source file.
public struct Lexer {

  /// The input being tokenized.
  public let source: String

  /// The current position of the lexer in `source`.
  public private(set) var position: String.Index

  /// Creates an instance tokening `source`.
  public init(tokenizing source: String) {
    self.source = source
    self.position = source.startIndex
  }

  /// Advances the lexer to `p`, which is after the current position.
  public mutating func advance(to p: String.Index) {
    assert(p > position)
    position = p
  }

  /// Advances to the next token and returns it, or returns `nil` if no next token exists.
  public mutating func next() -> Token? {
    if let unterminated = discardWhitespacesAndComments() { return unterminated }
    guard let head = peek() else { return nil }

    if let t = takeNumericLiteral() {
      return t
    } else if head == "\"" {
      return takeStringLiteral()
    } else if head == "$" {
      return takeVariable()
    } else if head == "`" {
      return takeQuotedIdentifier()
    } else if head.isIdentifierHead {
      return takeKeywordOrIdentifier()
    } else if head.isOperator {
      return takeRegex() ?? takeOperator()
    } else {
      return takePunctuation()
    }
  }

  /// Consumes and returns a numeric literal iff one can be scanned from the character stream.
  private mutating func takeNumericLiteral() -> Token? {
    let p = take("-") ?? position

    guard let h = peek(), h.isDecimalDigit else {
      position = p
      return nil
    }

    // Read the integer part.
    let q = take(while: { (c) in c.isDecimalDigit || (c == "_") }).endIndex

    // Is there a fractional part?
    if let i = take(".") {
      if takeDigitSequence(\.isDecimalDigit).isEmpty {
        position = i
        return .init(tag: .integerLiteral, site: p ..< q)
      }
    }

    // Is there an exponent?
    if let i = take("e") ?? take("E") {
      _ = take("+") ?? take("-")
      if takeDigitSequence(\.isDecimalDigit).isEmpty {
        position = i
      }
    }

    // No fractional part and no exponent.
    if position == q {
      return .init(tag: .integerLiteral, site: p ..< position)
    } else {
      return .init(tag: .floatingPointLiteral, site: p ..< position)
    }
  }

  /// Consumes and returns a string literal.
  private mutating func takeStringLiteral() -> Token {
    let start = position
    var escaped = false
    position = source.index(after: position)

    while position != source.endIndex {
      if source[position].isNewline {
        break
      } else if escaped {
        escaped = false
      } else if source[position] == "\\" {
        escaped = true
      } else if source[position] == "\"" {
        position = source.index(after: position)
        return .init(tag: .stringLiteral, site: start ..< position)
      }

      position = source.index(after: position)
    }

    return .init(tag: .unterminatedStringLiteral, site: start ..< position)
  }

  /// Consumes and returns the longest sequence that start with a digit and then contains either
  /// digits or the underscore, using `isDigit` to determine whether a character is a digit.
  private mutating func takeDigitSequence(_ isDigit: (Character) -> Bool) -> Substring {
    if let h = peek(), isDigit(h) {
      return take(while: { (c) in isDigit(c) || (c == "_") })
    } else {
      return source[position ..< position]
    }
  }

  /// Consumes and returns a variable.
  private mutating func takeVariable() -> Token {
    let start = position
    discard()
    let tail = take(while: \.isIdentifierTail)
    return .init(tag: tail.isEmpty ? .dollar : .variable, site: start ..< position)
  }

  /// Consumes and returns a keyword enclosed in backquotes.
  private mutating func takeQuotedIdentifier() -> Token {
    let start = position
    discard()
    let name = take(while: { (c) in c != "`" })

    if take("`") != nil {
      return .init(tag: .name, site: name.startIndex ..< name.endIndex)
    } else {
      return .init(tag: .unterminatedQuotedName, site: start ..< position)
    }
  }

  /// Consumes and returns a keyword or identifier.
  private mutating func takeKeywordOrIdentifier() -> Token {
    let word = take(while: \.isIdentifierTail)

    let tag: Token.Tag
    switch word {
    case "_": tag = .underscore
    case "else": tag = .else
    case "exit": tag = .exit
    case "if": tag = .if
    case "false": tag = .false
    case "load": tag = .load
    case "pmdb": tag = .pmdb
    case "select": tag = .select
    case "show": tag = .show
    case "then": tag = .then
    case "true": tag = .true
    default: tag = .name
    }

    assert(!word.isEmpty)
    return .init(tag: tag, site: word.startIndex ..< word.endIndex)
  }

  /// Consumes and returns a regex literal iff there is one starting at the current position.
  private mutating func takeRegex() -> Token? {
    if peek() != "/" { return nil }

    let start = position
    var escaped = false
    var i = source.index(after: position)

    while i != source.endIndex {
      if source[i].isNewline {
        return nil
      } else if escaped {
        escaped = false
      } else if source[i].isWhitespace {
        return nil
      } else if source[i] == "/" {
        break
      } else if source[i] == "\\" {
        escaped = true
      }

      i = source.index(after: i)
    }

    position = source.index(after: i)
    return .init(tag: .regex, site: start ..< position)
  }

  /// Consumes and returns an operator or a regex literal.
  private mutating func takeOperator() -> Token {
    let word = take(while: \.isOperator)

    let tag: Token.Tag
    switch word {
    case "=>": tag = .arrow
    case "=": tag = .assign
    default: tag = .operator
    }

    assert(!word.isEmpty)
    return .init(tag: tag, site: word.startIndex ..< word.endIndex)
  }

  /// Consumes and returns a punctuation token if possible; otherwise consumes a single character
  /// and returns an error token.
  private mutating func takePunctuation() -> Token {
    let start = position
    let tag: Token.Tag
    switch take() {
    case "{": tag = .leftBrace
    case "}": tag = .rightBrace
    case "[": tag = .leftBracket
    case "]": tag = .rightBracket
    case "(": tag = .leftParenthesis
    case ")": tag = .rightParenthesis
    case ",": tag = .comma
    case ":": tag = .colon
    case ".": tag = take("..") == nil ? .dot : .ellipsis
    default: tag = .error
    }
    return .init(tag: tag, site: start ..< position)
  }

  /// Returns the next character without consuming it or `nil` if all the input has been consumed.
  private func peek() -> Character? {
    position != source.endIndex ? source[position] : nil
  }

  /// Consumes and returns the next character.
  private mutating func take() -> Character {
    defer { position = source.index(after: position) }
    return source[position]
  }

  /// Returns the longest prefix of the input whose characters all satisfy `predicate` and advances
  /// the position of `self` until after that prefix.
  private mutating func take(while predicate: (Character) -> Bool) -> Substring {
    let start = position
    while (position != source.endIndex) && predicate(source[position]) {
      position = source.index(after: position)
    }
    return source[start ..< position]
  }

  /// If the input starts with `prefix`, returns the current position and advances to the position
  /// until after `prefix`. Otherwise, returns `nil`.
  private mutating func take(_ prefix: String) -> String.Index? {
    var newPosition = position
    for c in prefix {
      if newPosition == source.endIndex || source[newPosition] != c { return nil }
      newPosition = source.index(after: newPosition)
    }
    defer { position = newPosition }
    return position
  }

  /// Discards `count` characters.
  private mutating func discard(_ count: Int = 1) {
    position = source.index(position, offsetBy: count)
  }

  /// Discards characters until `predicate` isn't satisfied or all the input has been consumed.
  private mutating func discard(while predicate: (Character) -> Bool) {
    _ = take(while: predicate)
  }

  /// Discards all whitespaces and comments preceding the next token, returning an error token iff
  /// the scanner encounters an unmatched block comment opening sequence.
  private mutating func discardWhitespacesAndComments() -> Token? {
    while position != source.endIndex {
      if source[position].isWhitespace {
        discard()
      } else if take("#") != nil {
        discard(while: { (c) in !c.isNewline })
      } else {
        break
      }
    }
    return nil
  }

}

extension Character {

  /// `true` iff `self` is a letter or the underscore.
  fileprivate var isIdentifierHead: Bool {
    self.isLetter || self == "_"
  }

  /// `true` iff `self` is a letter, a decimal digit, or the underscore.
  fileprivate var isIdentifierTail: Bool {
    self.isIdentifierHead || self.isDecimalDigit
  }

  /// `true` iff `self` is a decimal digit.
  fileprivate var isDecimalDigit: Bool {
    asciiValue.map({ (ascii) in (0x30 ... 0x39) ~= ascii }) ?? false
  }

  /// `true` iff `self` may be part of an operator.
  fileprivate var isOperator: Bool {
    "<>=+-*/%&|!?^~".contains(self)
  }

}
