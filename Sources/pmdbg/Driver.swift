import ArgumentParser
import Foundation
import PostMortemDebugger

/// The top-level command of `pmdb`.
@main public struct Driver: ParsableCommand {

  /// `true` iff the command should just show the input trace.
  @Flag
  private var show: Bool = false

  /// The input file passed to the command.
  @Argument(transform: URL.init(fileURLWithPath:))
  private var input: URL

  /// Creates a new instance with default options.
  public init() {}

  /// Executes the command.
  public mutating func run() throws {
    let d = try Data(contentsOf: input)
    let t = try Trace(archive: d)

    if show {
      print(t)
    }
  }

}
