import Foundation

/// A file containing source code.
public struct SourceFile: Sendable {

  /// The raw contents of the file.
  public let contents: String

  /// A mapping from a line to the position immediately after its last character.
  public let lineEnds: [String.Index]

  /// Creates with the contents of `url`.
  public init?(contentsOf url: URL) {
    guard let s = try? String(contentsOf: url, encoding: .utf8) else { return nil }
    self.contents = s
    self.lineEnds = s.indices.reduce(into: []) { (es, i) in
      if s[i].isNewline { es.append(s.index(after: i)) }
    }
  }

  /// Returns the contents of the line at 1-based index `i`.
  public func line(_ i: Int) -> Substring {
    let s = (i == 1) ? contents.startIndex : lineEnds[i - 2]
    let e = lineEnds[i - 1]
    return contents[s ..< e]
  }

  /// The number of lines in the file.
  public var lineCount: Int {
    lineEnds.count
  }

}

extension SourceFile: Hashable {

  public func hash(into hasher: inout Hasher) {
    hasher.combine(contents)
  }

  public static func == (lhs: Self, rhs: Self) -> Bool {
    lhs.contents == rhs.contents
  }

}
