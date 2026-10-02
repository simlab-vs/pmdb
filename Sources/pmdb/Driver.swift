import ArgumentParser
import Foundation
import PostMortemDebugger

#if os(Windows)
  import ucrt
#endif

/// The top-level command of `pmdb`.
@main public struct Driver: AsyncParsableCommand {

  public static let configuration = CommandConfiguration(
    commandName: "pmdb",
    abstract: "A post-mortem debugger that answers queries about recorded execution traces.")

  /// `true` iff the traces passed as arguments should be shown instead of starting a session.
  @Flag(help: "Show the contents of the traces passed as arguments and exit.")
  private var show: Bool = false

  /// Whether observations are shown without excerpts of their source, if specified.
  @Flag(exclusivity: .chooseLast)
  private var excerpts: Excerpts?

  /// The trace that should be printed as XML, if any.
  @Option(
    name: .customLong("export-xml"),
    help: "Print the trace stored in the specified file as XML and exit.",
    transform: URL.init(fileURLWithPath:))
  private var exportXML: URL? = nil

  /// The input file passed to the command.
  @Argument(transform: URL.init(fileURLWithPath:))
  private var inputs: [URL] = []

  /// Whether `show` prints excerpts of the source of the observations it shows.
  private enum Excerpts: EnumerableFlag {

    /// Observations are shown without excerpts.
    case brief

    /// Observations are shown with excerpts.
    case nonBrief

    static func help(for value: Self) -> ArgumentHelp? {
      switch value {
      case .brief:
        "Show observations without excerpts of their source (default if the output isn't a terminal)."
      case .nonBrief:
        "Show observations with excerpts of their source (default if the output is a terminal)."
      }
    }

  }

  /// Creates a new instance with default options.
  public init() {}

  /// Checks the arguments of the command.
  public func validate() throws {
    if show && inputs.isEmpty {
      throw ValidationError("'--show' requires at least one trace")
    }
  }

  /// Executes the command.
  public mutating func run() async throws {
    // Should we just show the contents of the traces?
    if show {
      for u in inputs {
        do {
          try print(Trace(contentsOf: u), terminator: "")
        } catch let e {
          Self.report(e)
          throw ExitCode.failure
        }
      }
      return
    }

    // Should we just print a trace as XML?
    if let u = exportXML {
      do {
        try FileHandle.standardOutput.write(Trace(contentsOf: u).xml())
      } catch let e {
        Self.report(e)
        throw ExitCode.failure
      }
      return
    }

    try await runSession()
  }

  /// Runs the commands read from the standard input on the traces in `inputs`.
  ///
  /// The session is interactive iff the standard input is a terminal. An interactive session
  /// prompts for commands, pages the observations being shown, and reports errors without exiting.
  /// Other sessions exit with a failure at the first error.
  private func runSession() async throws {
    let interactive = Self.standardInputIsTerminal
    let brief = (excerpts ?? (Self.standardOutputIsTerminal ? .nonBrief : .brief)) == .brief
    var sources = AnyIterator({ Self.readSource(prompting: interactive) })

    /// Reports `e` and exits with a failure iff the session is not interactive.
    func handle(_ e: any Error) throws {
      Self.report(e)
      if !interactive { throw ExitCode.failure }
    }

    var engine = Engine()
    for url in inputs {
      do { try Self.load(url, into: &engine) } catch let e { try handle(e) }
    }
    while let s = sources.next() {
      // Skip lines holding only whitespace and comments.
      var tokens = Lexer(tokenizing: s)
      if tokens.next() == nil { continue }
      do {
        if try await !Self.execute(Self.parse(s), in: &engine, paged: interactive, brief: brief) {
          return
        }
      } catch let e {
        try handle(e)
      }
    }
  }

  /// Executes `command` on `engine`, paging the observations being shown iff `paged` is `true` and
  /// omitting excerpts of their source iff `brief` is `true`, and returns `false` iff it requests
  /// to exit.
  private static func execute(
    _ command: Command, in engine: inout Engine, paged: Bool, brief: Bool
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
      if v.count == 0, let n = engine.noteOnUnrecordedFunction(of: q) { warning(n) }

    case .show(let x):
      switch try engine.value(for: x) {
      case .observations(let v):
        show(v, in: &engine, paged: paged, brief: brief)
      case .trace(let v):
        print(engine.trace(v))
      }

    case .showConvenienceVariables:
      for (k, v) in engine.definitions {
        print("\(k) : \(v.type)")
      }

    case .export(let x, let path):
      guard case .observations(let v) = try engine.value(for: x) else {
        throw RuntimeError("'\(x)' isn't the result of a query")
      }
      var lines: [String] = []
      for i in v.traces.indices {
        let trace = engine.trace(v.traces[i])
        var snaps = v.snaps(in: i)[...]
        var calls = v.calls(in: i)[...]
        while true {
          if let c = calls.first, snaps.first.map({ (s) in c.untagged < s.untagged }) ?? true {
            lines.append(trace.json(call: calls.removeFirst()))
          } else if let s = snaps.first {
            snaps.removeFirst()
            lines.append(Trace.json(snap: trace[at: s]))
          } else {
            break
          }
        }
      }
      do {
        try lines.map({ $0 + "\n" }).joined().write(toFile: path, atomically: true, encoding: .utf8)
      } catch let e {
        throw RuntimeError("cannot write '\(path)': \(e.localizedDescription)")
      }
      print("exported \(lines.count) observation(s) of \(x) to \(path)")

    case .showFunctions:
      for (f, n) in engine.callCounts.sorted(by: { (a, b) in a.key < b.key }) {
        print("\(f): \(n) call(s)")
      }
    }
    return true
  }

  private static func show(_ trace: Trace) {
    print(trace)
  }

  /// Writes a description of `source` to the standard output, asking whether to continue after
  /// each observation iff `paged` is `true` and omitting excerpts of the source iff `brief` is
  /// `true`.
  private static func show<T: ObservationSet>(
    _ source: T, in engine: inout Engine, paged: Bool, brief: Bool
  ) {
    for i in source.traces.indices {
      let trace = engine.trace(source.traces[i])
      var snaps = source.snaps(in: i)[...]
      var calls = source.calls(in: i)[...]

      // Show snaps and calls in the order in which they were observed.
      while true {
        if let c = calls.first, snaps.first.map({ (s) in c.untagged < s.untagged }) ?? true {
          let c = calls.removeFirst()
          show(trace[at: c], described: trace.description(of: c), in: &engine, brief: brief)
        } else if !snaps.isEmpty {
          let s = trace[at: snaps.removeFirst()]
          show(s, described: s.description, in: &engine, brief: brief)
        } else {
          break
        }

        // Should we exit early?
        if paged && !yesOrNo("continue?") { return }
      }
    }
  }

  /// Writes `description`, which describes `o`, and an excerpt of the source of `o` unless `brief`
  /// is `true` to the standard output.
  private static func show<T: Observation>(
    _ o: T, described description: String, in engine: inout Engine, brief: Bool
  ) {
    print("\(o.location): \(description)")
    if brief { return }
    if let s = engine.demand(contentsOf: URL(fileURLWithPath: o.location.source)) {
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

  /// `true` iff the standard input is a terminal.
  private static var standardInputIsTerminal: Bool {
    #if os(Windows)
      _isatty(0) != 0
    #else
      isatty(STDIN_FILENO) != 0
    #endif
  }

  /// `true` iff the standard output is a terminal.
  private static var standardOutputIsTerminal: Bool {
    #if os(Windows)
      _isatty(1) != 0
    #else
      isatty(STDOUT_FILENO) != 0
    #endif
  }

  /// Returns the next source read from the standard input, prompting for it iff `prompting` is
  /// `true`, or returns `nil` if the input is exhausted.
  ///
  /// A source spans several lines if they end with a line continuation.
  private static func readSource(prompting: Bool) -> String? {
    var source = ""

    while true {
      // Read the contents of the line from the standar input.
      if prompting { print(style.prompt("(pmdb)"), terminator: " ") }
      guard let data = readLine() else {
        return source.isEmpty ? nil : source
      }

      // A line ending with a backslash continues on the next, unless the backslash is part of a
      // string literal, which is delimited by double quotes, or of a comment, which extends from
      // a number sign to the end of the line.
      var inString = false
      var escaped = false
      var inComment = false
      for c in data {
        if inString {
          if escaped {
            escaped = false
          } else if c == "\\" {
            escaped = true
          } else if c == "\"" {
            inString = false
          }
        } else if c == "#" {
          inComment = true
          break
        } else if c == "\"" {
          inString = true
        }
      }

      if !inString && !inComment && (data.last == "\\") {
        source.write(String(data.dropLast()))
      } else {
        source.write(data)
        return source
      }
    }
  }

  /// Returns the command parsed from `source`, reporting warnings to the standard error.
  private static func parse(_ source: String) throws -> Command {
    var parser = Parser(source)
    let result = try parser.parseCommand()
    parser.diagnostics.forEach(report(_:))

    // Make sure we parsed the whole input.
    let r = parser.remainder()
    if !r.isEmpty {
      let m = "expected end of command, found '\(r)'"
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

    // Flush the standard output first so that errors appear after the output preceding them.
    fflush(nil)
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
    fflush(nil)
    var m = Self.style.warning("warning: ")
    m.write(message)
    m.write("\n")
    FileHandle.standardError.write(m.data(using: .utf8)!)
  }

  /// The style sheet of the REPL, which colors output only if it is written to a terminal.
  private static let style: TextOutputStyle =
    (ProcessInfo.ansiTerminalIsConnected && standardOutputIsTerminal) ? .styled : .unstyled

}

extension String {

  /// Returns `self` prefixed by spaces to fit `width` columns.
  fileprivate func leftPaddedTo(_ width: Int) -> String {
    (width <= count) ? self : String(repeating: " ", count: width - count) + self
  }

}
