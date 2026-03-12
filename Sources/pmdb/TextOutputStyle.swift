import Foundation
import PostMortemDebugger

/// Style transforms applied to the raw text of different parts of a diagnostic.
internal struct TextOutputStyle: Sendable {

  /// How a prompt is rendered in this style.
  internal let prompt: String.ANSIStyle

  /// How a command result is rendered in tis style.
  internal let result: String.ANSIStyle

  /// How an error label is rendered in this style.
  internal let error: String.ANSIStyle

  /// How a warning label is rendered in this style.
  internal let warning: String.ANSIStyle

  /// How a label for diagnostic level `l` is rendered in this style.
  internal subscript(l: Diagnostic.Level) -> String.ANSIStyle {
    switch l {
    case .error: error
    case .warning: warning
    }
  }

  /// The identity style; applies no changes to text.
  internal static let unstyled = TextOutputStyle(
    prompt: String.unstyled,
    result: String.unstyled,
    error: String.unstyled,
    warning: String.unstyled)

  /// The default style with colors and font weights.
  internal static let styled = TextOutputStyle(
    prompt: { (s) in s.styled(.dimmed) },
    result: { (s) in s.styled(.cyan) },
    error: { (s) in s.styled(.bold, .red) },
    warning: { (s) in s.styled(.bold, .yellow) })

}

/// An ANSI [Select Graphic Rendition](https://en.wikipedia.org/wiki/ANSI_escape_code#SGR) (SGR)
/// escape code.
internal enum ANSISGR: Int {

  /// Reset all SGR attributes
  case reset = 0

  case bold = 1
  case dimmed = 2
  case italic = 3
  case underline = 4
  case blink = 5
  case strike = 9
  case defaultFont = 10
  case black = 30
  case red = 31
  case green = 32
  case yellow = 33
  case blue = 34
  case magenta = 35
  case cyan = 36
  case white = 37
  case defaultColor = 39

  /// The textual representation of this code that has an effect on an ANSI terminal.
  internal var controlString: String {
    "\u{001B}[\(rawValue)m"
  }

}

extension String {

  /// A string transformation for applying (or not) ANSI terminal styling.
  internal typealias ANSIStyle = @Sendable (String) -> String

  /// Returns `self` with the given set of styles applied.
  internal func styled(_ rendition: ANSISGR...) -> String {
    var result = ""
    result.append("\(rendition.map(\.controlString).joined())")
    result.append("\(self)\(ANSISGR.reset.controlString)")
    return result
  }

  /// The identity transformation.
  internal static let unstyled: ANSIStyle = { $0 }

}

extension ProcessInfo {

  /// `true` iff the terminal supports coloring.
  internal static let ansiTerminalIsConnected =
    !["", "dumb", nil].contains(processInfo.environment["TERM"])

}
