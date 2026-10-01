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

  /// Creates a new instance with default options.
  public init() {}

  /// Executes the command.
  public mutating func run() async throws {
    // Should we just show the contents of a trace?
    if let u = show {
      Self.attempt({ try print(Trace(contentsOf: u)) })
      return
    }

    // Start the REPL.
    var engine = Engine()
    for url in inputs {
      Self.load(url, into: &engine)
    }

    while true {
      guard let command = Self.attempt(Self.readCommand) else { continue }
      switch command {
      case .exit:
        Self.exit()

      case .load(let url, let x):
        Self.load(url, assignedTo: x, into: &engine)

      case .select(let q):
        do {
          let v = try await engine.select(q)
          let k = engine.fresh()
          engine.assign(.observations(v), for: k)
          print(Self.style.result("\(k) = <\(v.count) element(s) in \(v.traces.count) trace(s)>"))
        } catch let e {
          Self.report(e)
        }

      case .show(let x):
        Self.show(x, in: &engine)

      case .showConvenienceVariables:
        for (k, v) in engine.definitions {
          print("\(k) : \(v.type)")
        }
      }
    }
  }

  /// Writes a description of the value assigned to `variable` to the standard output.
  private static func show(_ variable: String, in engine: inout Engine) {
    Self.attempt {
      switch try engine.value(for: variable) {
      case .observations(let v):
        show(v, in: &engine)
      case .trace(let v):
        print(engine.trace(v))
      }
    }
  }

  private static func show(_ trace: Trace) {
    print(trace)
  }

  /// Writes a description of `source` to the standard output.
  private static func show<T: ObservationSet>(_ source: T, in engine: inout Engine) {
    for i in source.traces.indices {
      let trace = engine.trace(source.traces[i])
      var snaps = source.snaps(in: i)[...]
      var calls = source.calls(in: i)[...]

      var loop = true
      while loop {
        switch (snaps.first, calls.first) {
        case (.some(let l), .some(let r)) where r.untagged < l.untagged:
          show(trace[at: calls.removeFirst()], in: &engine)
        case (.some, .some):
          show(trace[at: snaps.removeFirst()], in: &engine)
        case (.some, _):
          show(trace[at: snaps.removeFirst()], in: &engine)
        case (_, .some):
          show(trace[at: calls.removeFirst()], in: &engine)
        case (_, _):
          loop = false
        }

        // Should we exit early?
        if loop && !yesOrNo("continue?") { return }
      }
    }
  }

  /// Writes a description of `o` to the standard output.
  private static func show<T: Observation>(_ o: T, in engine: inout Engine) {
    print("\(o.location): \(o)")
    if let s = engine.demand(contentsOf: URL(fileURLWithPath: o.location.source)) {
      let n = o.location.number
      for i in stride(from: max(1, n - 2), through: min(s.lineCount, n + 2), by: 1) {
        let marker = (i == o.location.number) ? "> " : "  "
        let gutter = style.prompt("\(String(i).leftPaddedTo(4)) | ")
        print("\(marker)\(gutter)\(s.line(i))", terminator: "")
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

    // Parse the command.
    var parser = Parser(line)
    let result = try parser.parseCommand()
    parser.diagnostics.forEach(report(_:))

    // Make we parsed the whole line.
    let r = parser.remainder()
    if !r.isEmpty {
      let m = "multiple commands should be separated by a newline"
      report(Diagnostic(.error, m, at: r.startIndex ..< r.startIndex))
    }

    return result
  }

  /// Parses a trace from the archive at the given URL and loads them into `engine`, reporting
  /// errors to the standard error.
  @discardableResult
  private static func load(
    _ trace: URL, assignedTo name: String? = nil, into engine: inout Engine
  ) -> Trace.ID? {
    if let t = attempt({ try Trace(contentsOf: trace) }) {
      engine.add(t)
      if let n = name { engine.assign(.trace(t.identity), for: n) }
      return t.identity
    } else {
      return nil
    }
  }

  /// Returns the result of `action()` iff it does not throw. Otherwise, reports the error to the
  /// standard error and returns `nil`.
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
