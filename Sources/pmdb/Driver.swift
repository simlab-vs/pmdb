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

  /// The trace that should be printed as XML, if any.
  @Option(
    name: .customLong("export-xml"),
    help: "Print the trace stored in the specified file as XML and exit.",
    transform: URL.init(fileURLWithPath:))
  private var exportXML: URL? = nil

  /// The input file passed to the command.
  @Argument(transform: URL.init(fileURLWithPath:))
  private var inputs: [URL] = []

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
      if s.allSatisfy(\.isWhitespace) { continue }
      do {
        if try await !Self.execute(Self.parse(s), in: &engine, paged: interactive) { return }
      } catch let e {
        try handle(e)
      }
    }
  }

  /// Executes `command` on `engine`, paging the observations being shown iff `paged` is `true`,
  /// and returns `false` iff it requests to exit.
  private static func execute(
    _ command: Command, in engine: inout Engine, paged: Bool
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

    case .show(let x):
      switch try engine.value(for: x) {
      case .observations(let v):
        show(v, in: &engine, paged: paged)
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

  /// Writes a description of `source` to the standard output, asking whether to continue after
  /// each observation iff `paged` is `true`.
  private static func show<T: ObservationSet>(
    _ source: T, in engine: inout Engine, paged: Bool
  ) {
    for i in source.traces.indices {
      let trace = engine.trace(source.traces[i])
      var snaps = source.snaps(in: i)[...]
      var calls = source.calls(in: i)[...]

      // Show snaps and calls in the order in which they were observed.
      while true {
        if let c = calls.first, snaps.first.map({ (s) in c.untagged < s.untagged }) ?? true {
          let c = calls.removeFirst()
          show(trace[at: c], described: trace.description(of: c), in: &engine)
        } else if !snaps.isEmpty {
          let s = trace[at: snaps.removeFirst()]
          show(s, described: s.description, in: &engine)
        } else {
          break
        }

        // Should we exit early?
        if paged && !yesOrNo("continue?") { return }
      }
    }
  }

  /// Writes `description`, which describes `o`, and an excerpt of the source of `o` to the
  /// standard output.
  private static func show<T: Observation>(
    _ o: T, described description: String, in engine: inout Engine
  ) {
    print("\(o.location): \(description)")
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
  /// A source spans several lines if they end with a line continuation or an unterminated string.
  private static func readSource(prompting: Bool) -> String? {
    var line = ""
    var inString = false
    var escaped = false
    var prompt = "(pmdb)"

    while true {
      // Read the contents of the line from the standar input.
      if prompting { print(style.prompt(prompt), terminator: " ") }
      guard let data = readLine() else {
        return line.isEmpty ? nil : line
      }
      line.write(data)

      // Check for line continuations.
      if line.last == "\\" {
        line.removeLast()
        continue
      }

      // Check for non-terminated string literals, which are delimited by double quotes.
      for c in data {
        if escaped {
          escaped = false
        } else if inString && (c == "\\") {
          escaped = true
        } else if c == "\"" {
          inString.toggle()
        }
      }

      // Prepare the next prompt if we found a non-terminated string.
      if inString {
        prompt = "   \" )"
      } else {
        return line
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
