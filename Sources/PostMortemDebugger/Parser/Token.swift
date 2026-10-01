/// A terminal symbol of the syntactic grammar.
public struct Token: Hashable, Sendable {

  /// The tag of a token.
  public enum Tag: UInt8, Sendable {

    // Identifiers and variables.
    case name
    case underscore
    case `else`
    case exit
    case `false`
    case `if`
    case load
    case noneLiteral
    case pmdb
    case select
    case show
    case then
    case `true`

    // Variables and regex literals
    case variable
    case regex

    // Scalar literals
    case integerLiteral
    case floatingPointLiteral
    case stringLiteral

    // Operators
    case `operator`
    case arrow
    case assign
    case dollar

    // Punctuation
    case comma
    case dot
    case colon
    case ellipsis

    // Delimiters
    case leftBrace
    case rightBrace
    case leftBracket
    case rightBracket
    case leftParenthesis
    case rightParenthesis

    // Errors
    case error
    case unterminatedQuotedName
    case unterminatedStringLiteral

  }

  /// The tag of the token.
  public let tag: Tag

  /// The text of the token.
  public let site: Range<String.Index>

  /// Creates an instance with the given properties.
  public init(tag: Tag, site: Range<String.Index>) {
    self.tag = tag
    self.site = site
  }

  /// Returns a lambda accepting a token and returning `true` iff that token has tag `tag`.
  public static func hasTag(_ tag: Tag) -> (Token) -> Bool {
    { (t) in t.tag == tag }
  }

}
