import ArgumentParser
import Foundation
import PostMortemDebugger

/// The top-level command of `pmdb`.
@main public struct Driver: AsyncParsableCommand {

  /// The trace that should be shown, if any.
  @Option(
    help: "Show the contents of the trace stored in the specified file and exit.",
    transform: URL.init(fileURLWithPath:))
  private var show: URL? = nil

  /// The input file passed to the command.
  @Argument(transform: URL.init(fileURLWithPath:))
  private var inputs: [URL] = []

  /// The commands to execute instead of starting the REPL.
  @Option(
    name: [.customShort("e"), .customLong("execute")],
    help: "Execute the given command and exit instead of starting the REPL. Can be repeated.")
  private var commands: [String] = []

  /// Creates a new instance with default options.
  public init() {}

  /// Executes the command.
  public mutating func run() async throws {
    // Should we just show the contents of a trace?
    if let u = show {
      Self.attempt({ try print(Trace(contentsOf: u)) })
      return
    }

    if commands.isEmpty {
      await repl()
    } else {
      try await executeCommands()
    }
  }

  /// Runs a REPL on the traces in `inputs`, reporting errors without exiting.
  private func repl() async -> Never {
    var engine = Engine()
    for url in inputs {
      Self.attempt({ try Self.load(url, into: &engine) })
    }

    while true {
      guard let command = Self.attempt(Self.readCommand) else { continue }
      do {
        if try await !Self.execute(command, in: &engine, interactive: true) { Self.exit() }
      } catch let e {
        Self.report(e)
      }
    }
  }

  /// Executes `commands` on the traces in `inputs`, exiting with a failure at the first error.
  private func executeCommands() async throws {
    do {
      var engine = Engine()
      for url in inputs {
        try Self.load(url, into: &engine)
      }
      for c in commands {
        if try await !Self.execute(Self.parse(c), in: &engine, interactive: false) { return }
      }
    } catch let e {
      Self.report(e)
      throw ExitCode.failure
    }
  }

  /// Executes `command` on `engine` and returns `false` iff it requests to exit.
  ///
  /// The observations selected by a query are listed iff `interactive` is `false`. Otherwise, the
  /// observations being shown are paged.
  private static func execute(
    _ command: Command, in engine: inout Engine, interactive: Bool
  ) async throws -> Bool {
    switch command {
    case .exit:
      return false

    case .load(let url, let x):
      try Self.load(url, assignedTo: x, into: &engine)

    case .select(let q):
      let v = try await engine.select(q)
      let k = engine.fresh()
      engine.assign(.observations(v), for: k)
      print(Self.style.result("\(k) = <\(v.count) element(s) in \(v.traces.count) trace(s)>"))
      if !interactive { show(v, in: &engine, withExcerpts: false, paged: false) }

    case .show(let x):
      switch try engine.value(for: x) {
      case .observations(let v):
        show(v, in: &engine, withExcerpts: true, paged: interactive)
      case .trace(let v):
        print(engine.trace(v))
      }

    case .showConvenienceVariables:
      for (k, v) in engine.definitions {
        print("\(k) : \(v.type)")
      }
    }
    return true
  }

  private static func show(_ trace: Trace) {
    print(trace)
  }

  /// Writes a description of `source` to the standard output, with source excerpts iff
  /// `withExcerpts` is `true`, asking whether to continue after each observation iff `paged` is
  /// `true`.
  private static func show<T: ObservationSet>(
    _ source: T, in engine: inout Engine, withExcerpts: Bool, paged: Bool
  ) {
    for i in source.traces.indices {
      let trace = engine.trace(source.traces[i])
      var snaps = source.snaps(in: i)[...]
      var calls = source.calls(in: i)[...]

      // Show snaps and calls in the order in which they were observed.
      while true {
        if let c = calls.first, snaps.first.map({ (s) in c.untagged < s.untagged }) ?? true {
          show(trace[at: calls.removeFirst()], in: &engine, withExcerpts: withExcerpts)
        } else if !snaps.isEmpty {
          show(trace[at: snaps.removeFirst()], in: &engine, withExcerpts: withExcerpts)
        } else {
          break
        }

        // Should we exit early?
        if paged && !yesOrNo("continue?") { return }
      }
    }
  }

  /// Writes a description of `o` to the standard output, with a source excerpt iff `withExcerpts`
  /// is `true`.
  private static func show<T: Observation>(
    _ o: T, in engine: inout Engine, withExcerpts: Bool
  ) {
    print("\(o.location): \(o)")
    if withExcerpts, let s = engine.demand(contentsOf: URL(fileURLWithPath: o.location.source)) {
      let n = o.location.number
      for i in stride(from: max(1, n - 2), through: min(s.lineCount, n + 2), by: 1) {
        let marker = (i == o.location.number) ? "> " : "  "
        let gutter = style.prompt("\(String(i).leftPaddedTo(4)) | ")
        let l = s.line(i)
        print("\(marker)\(gutter)\(l.last?.isNewline ?? false ? l.dropLast() : l)")
      }
    }
  }

  /// Asks the user for a yes/no answer to `question` and returns `true` iff the answer is "yes".
  fileprivate static func yesOrNo(_ question: String) -> Bool {
    while true {
      print(style.prompt("\(question) [Y/n]"), terminator: " ")
      guard let s = readLine() else { return false }
      if s.isEmpty || (s == "Y") || (s == "y") {
        return true
      } else if s == "n" {
        return false
      }
    }
  }

  /// Returns a command parsed from the standard input.
  private static func readCommand() throws -> Command {
    var line = ""
    var stack: [Character] = []
    var prompt = "(pmdb)"

    while true {
      // Read the contents of the line from the standar input.
      print(style.prompt(prompt), terminator: " ")
      guard let data = readLine() else {
        if line.isEmpty { Self.exit() }
        break
      }
      line.write(data)

      // Check for line continuations.
      if line.last == "\\" {
        line.removeLast()
        continue
      }

      // Check for non-terminated string literals.
      for c in data where c == "'" || c == "\"" {
        if stack.last == c { stack.removeLast() } else { stack.append(c) }
      }

      // Prepare the next prompt if we found a non-terminated delimited string.
      if let last = stack.last {
        prompt = "   \(last) )"
      } else {
        break
      }
    }

    return try parse(line)
  }

  /// Returns the command parsed from `source`, reporting warnings to the standard error.
  private static func parse(_ source: String) throws -> Command {
    var parser = Parser(source)
    let result = try parser.parseCommand()
    parser.diagnostics.forEach(report(_:))

    // Make sure we parsed the whole input.
    let r = parser.remainder()
    if !r.isEmpty {
      let m = "multiple commands should be separated by a newline"
      throw Diagnostic(.error, m, at: r.startIndex ..< r.startIndex)
    }

    return result
  }

  /// Parses a trace from the archive at the given URL and loads it into `engine`, assigning it to
  /// `name` if provided.
  private static func load(
    _ trace: URL, assignedTo name: String? = nil, into engine: inout Engine
  ) throws {
    let t = try Trace(contentsOf: trace)
    engine.add(t)
    if let n = name { engine.assign(.trace(t.identity), for: n) }
  }

  /// Returns the result of `action()` iff it does not throw. Otherwise, reports the error to the
  /// standard error and returns `nil`.
  @discardableResult
  private static func attempt<T>(_ action: () throws -> T) -> T? {
    do {
      return try action()
    } catch let e {
      report(e)
      return nil
    }
  }

  /// Reports `e` to the standard error.
  private static func report(_ e: any Error) {
    var m = ""

    switch e {
    case let d as Diagnostic:
      m.write(Self.style[d.level]("\(d.level): "))
      m.write(d.message)
    case let d as RuntimeError:
      m.write(Self.style.error("error: "))
      m.write(String(describing: d))
    case let d:
      m.write(Self.style.error("error: "))
      m.write(d.localizedDescription)
    }

    m.write("\n")
    FileHandle.standardError.write(m.data(using: .utf8)!)
  }

  /// Reports `message` as an error to the standard error.
  private static func error(_ message: String) {
    var m = Self.style.error("error: ")
    m.write(message)
    m.write("\n")
    FileHandle.standardError.write(m.data(using: .utf8)!)
  }

  /// Reports `message` as a warning to the standard error.
  private static func warning(_ message: String) {
    var m = Self.style.warning("warning: ")
    m.write(message)
    m.write("\n")
    FileHandle.standardError.write(m.data(using: .utf8)!)
  }

  /// The style sheet of the REPL.
  private static let style: TextOutputStyle =
    ProcessInfo.ansiTerminalIsConnected ? .styled : .unstyled

}

extension String {

  /// Returns `self` prefixed by spaces to fit `width` columns.
  fileprivate func leftPaddedTo(_ width: Int) -> String {
    (width <= count) ? self : String(repeating: " ", count: width - count) + self
  }

}
