import Foundation
import Subprocess
import Testing

#if canImport(System)
  import System
#else
  import SystemPackage
#endif

/// The outcome of a run of `pmdb`.
private struct Outcome {

  /// `true` iff `pmdb` exited successfully.
  let succeeded: Bool

  /// The contents of the standard output, without trailing whitespace.
  let output: String

  /// The contents of the standard error, without trailing whitespace.
  let error: String

}

/// An error indicating that `pmdb` did not exit in time.
private struct Timeout: Error {}

/// Returns a file descriptor reading `contents` from a temporary file.
///
/// Inputs are read from files rather than pipes because `pmdb` can exit before reading its input
/// (e.g., if a trace can't be loaded), and writing to a pipe whose reader has exited fails.
private func inputFile(_ contents: String) throws -> FileDescriptor {
  let path = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try contents.write(to: path, atomically: true, encoding: .utf8)
  let descriptor = try FileDescriptor.open(FilePath(path.path), .readOnly)

  // An open file can be removed without closing its descriptors, except on Windows.
  #if !os(Windows)
    try FileManager.default.removeItem(at: path)
  #endif
  return descriptor
}

/// Returns the outcome of running `pmdb` with `arguments`, feeding `input` to its standard input,
/// or throws `Timeout` if it does not exit within `timeLimit`.
///
/// The output and the error are normalized; see `String.normalized`.
private func pmdb(_ arguments: [String] = [], input: String = "") async throws -> Outcome {
  let source = try inputFile(input)
  return try await withThrowingTaskGroup(of: Outcome.self) { (group) in
    group.addTask {
      let result = try await run(
        .path(.init(pmdbExecutable.path)),
        arguments: .init(arguments),
        environment: .inherit.updating(["TERM": "dumb"]),
        input: .fileDescriptor(source, closeAfterSpawningProcess: true),
        output: .string(limit: 1 << 20),
        error: .string(limit: 1 << 20))
      return Outcome(
        succeeded: result.terminationStatus.isSuccess,
        output: result.standardOutput.normalized,
        error: result.standardError.normalized)
    }
    group.addTask {
      try await Task.sleep(for: timeLimit)
      throw Timeout()
    }

    // Cancelling the run kills `pmdb`.
    defer { group.cancelAll() }
    return try await group.next()!
  }
}

/// The time after which a run of `pmdb` is considered to wait for input forever.
///
/// It is generous because tests run in parallel, possibly on slow machines and in debug builds.
/// Starting processes on Windows CI machines takes up to half a minute when many tests run at once.
#if os(Windows)
  private let timeLimit = Duration.seconds(60)
#else
  private let timeLimit = Duration.seconds(10)
#endif

/// A class identifying the bundle containing these tests.
private final class TestBundleMarker {}

/// The `pmdb` executable, which is built next to the test products.
private let pmdbExecutable: URL = {
  #if os(macOS)
    // The tests are in a bundle `pmdbTests.xctest`, which may not be listed in `Bundle.allBundles`
    // depending on the program loading it.
    let products = Bundle(for: TestBundleMarker.self).bundleURL.deletingLastPathComponent()
  #else
    let products = Bundle.main.bundleURL
  #endif
  return products.appendingPathComponent("pmdb")
}()

extension String {

  /// `self` with its line endings written `\n`, which Windows writes `\r\n`, and without trailing
  /// whitespace and line separators.
  fileprivate var normalized: String {
    var s = self.replacingOccurrences(of: "\r\n", with: "\n")
    while s.last?.isWhitespace ?? false { s.removeLast() }
    return s
  }

}

/// A trace and the source file in which it was recorded.
private struct Recording {

  /// The path of the trace.
  let trace: String

  /// The path of the source file.
  let source: String

}

/// Writes `source` and a trace with one call to `f` at `line` of `source` in a fresh directory,
/// followed by the observations in `following`, which are XML elements.
private func makeTrace(
  source: String = "def f(x):\n  return x\nf(1)\n", callingAt line: Int = 3,
  following: String = ""
) throws -> Recording {
  let directory = FileManager.default.temporaryDirectory
    .appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

  let s = directory.appendingPathComponent("a.py")
  try source.write(to: s, atomically: true, encoding: .utf8)

  let t = directory.appendingPathComponent("a.xml")
  try """
    <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
      <pmdb:observations>
        <pmdb:call location="\(s.path):\(line)">
          <pmdb:function>root</pmdb:function>
          <pmdb:arguments/>
          <pmdb:observations>
            <pmdb:call location="\(s.path):\(line)">
              <pmdb:function>f</pmdb:function>
              <pmdb:arguments><pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value></pmdb:arguments>
            </pmdb:call>
            \(following)
          </pmdb:observations>
        </pmdb:call>
      </pmdb:observations>
    </pmdb:trace>
    """.write(to: t, atomically: true, encoding: .utf8)
  return Recording(trace: t.path, source: s.path)
}

@Test func selectsFromLoadedTrace() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x)\nexit\n")
  #expect(o.succeeded)
  #expect(o.output == "$0 = <1 element(s) in 1 trace(s)>")
  #expect(o.error == "")
}

@Test func exitsAtEndOfInput() async throws {
  let o = try await pmdb()
  #expect(o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "")
}

@Test func stopsAtFirstFailingLineOfInput() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x) from $nope\nselect f(x)\n")
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: undefined symbol '$nope'")
}

@Test func ignoresBlankLinesOfInput() async throws {
  let o = try await pmdb([makeTrace().trace], input: "\nselect f(x)\n  \n")
  #expect(o.succeeded)
  #expect(o.output == "$0 = <1 element(s) in 1 trace(s)>")
  #expect(o.error == "")
}

@Test func showsWithoutReadingAnswersFromInput() async throws {
  let r = try makeTrace()
  let o = try await pmdb(["--non-brief", r.trace], input: "select f(x)\nshow $0\nselect f(x)\n")
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):3: call f(1)
         1 | def f(x):
         2 |   return x
    >    3 | f(1)
    $1 = <1 element(s) in 1 trace(s)>
    """)
  #expect(o.error == "")
}

@Test(arguments: [[], ["--brief"], ["--non-brief", "--brief"]])
func showsBrieflyWhenOutputIsNotTerminal(flags: [String]) async throws {
  let r = try makeTrace()
  let o = try await pmdb(flags + [r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):3: call f(1)
    """)
}

@Test func showsRecordedFunctions() async throws {
  let o = try await pmdb([makeTrace().trace], input: "show functions\n")
  #expect(o.succeeded)
  #expect(o.output == "f: 1 call(s)")
}

@Test func reportsWhatShowExpects() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x)\nshow trace.pmdb\n")
  #expect(!o.succeeded)
  #expect(o.error == "error: expected a variable such as $0, 'variables', or 'functions'")
}

/// A source file of seven lines.
private let sevenLines = "a\nb\nc\nd\ne\nf\ng\n"

@Test(arguments: [
  (1, """
    >    1 | a
         2 | b
         3 | c
    """),
  (2, """
         1 | a
    >    2 | b
         3 | c
         4 | d
    """),
  (4, """
         2 | b
         3 | c
    >    4 | d
         5 | e
         6 | f
    """),
  (6, """
         4 | d
         5 | e
    >    6 | f
         7 | g
    """),
  (7, """
         5 | e
         6 | f
    >    7 | g
    """),
  (8, """
         6 | f
         7 | g
    """),
])
func showsSourceExcerpt(line: Int, excerpt: String) async throws {
  let r = try makeTrace(source: sevenLines, callingAt: line)
  let o = try await pmdb(["--non-brief", r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):\(line): call f(1)
    \(excerpt)
    """)
  #expect(o.error == "")
}

@Test func showsObservationPastEndOfSource() async throws {
  let r = try makeTrace(source: sevenLines, callingAt: 10)
  let o = try await pmdb(["--non-brief", r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):10: call f(1)
    """)
  #expect(o.error == "")
}

@Test func showsLastLineWithoutLineSeparator() async throws {
  let r = try makeTrace(source: "a\nb", callingAt: 2)
  let o = try await pmdb(["--non-brief", r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):2: call f(1)
         1 | a
    >    2 | b
    """)
  #expect(o.error == "")
}

/// The output of the commands in `sessionCommands`.
private func sessionOutput(_ r: Recording) -> String {
  """
  $0 = <1 element(s) in 1 trace(s)>
  $1 = <1 element(s) in 1 trace(s)>
  \(r.source):3: call f(1)
       1 | def f(x):
       2 |   return x
  >    3 | f(1)
  """
}

/// Commands that select a call, select from that selection, and show the result.
private let sessionCommands = ["select f(x)", "select _(...) from $0", "show $1"]

@Test func executesCommandsFromInput() async throws {
  let r = try makeTrace()
  let o = try await pmdb(["--non-brief", r.trace], input: sessionCommands.joined(separator: "\n") + "\n")
  #expect(o.succeeded)
  #expect(o.output == sessionOutput(r))
  #expect(o.error == "")
}

@Test func rejectsTrailingInput() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x) )\n")
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: expected end of command, found ')'")
}

@Test func exitStopsExecution() async throws {
  let o = try await pmdb([makeTrace().trace], input: "exit\nselect f(x)\n")
  #expect(o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "")
}

@Test func failsOnUnloadableTraceWithCommandsFromInput() async throws {
  let o = try await pmdb(["missing.trace"], input: "select f(x)\n")
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: cannot read 'missing.trace': no such file")
}

@Test func reportsEvaluationErrors() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x) where x.y\n")
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: value of type 'integer' is not a table")
}

@Test func exportsTraceToXML() async throws {
  let r = try makeTrace()
  let o = try await pmdb(["--export-xml", r.trace])
  #expect(o.succeeded)
  #expect(o.output.contains("<pmdb:function>f</pmdb:function>"))
  #expect(o.output.contains("<pmdb:integer>1</pmdb:integer>"))
  #expect(o.error == "")

  // The output can be loaded back.
  let exported = FileManager.default.temporaryDirectory
    .appendingPathComponent(UUID().uuidString + ".xml")
  try o.output.write(to: exported, atomically: true, encoding: .utf8)
  let p = try await pmdb([exported.path], input: "select f(x) where x == 1\n")
  #expect(p.succeeded)
  #expect(p.output.hasPrefix("$0 = <1 element(s) in 1 trace(s)>"))
}

@Test(arguments: [true, false])
func showsTraces(flagFirst: Bool) async throws {
  let r = try makeTrace()
  let o = try await pmdb(flagFirst ? ["--show", r.trace] : [r.trace, "--show"])
  #expect(o.succeeded)
  #expect(o.output == """
    * call root()
    └─* call f(1)
    """)
  #expect(o.error == "")
}

@Test func failsToShowUnloadableTrace() async throws {
  let o = try await pmdb(["--show", "missing.trace"])
  #expect(!o.succeeded)
  #expect(o.output == "")
}

@Test func requiresTraceToShow() async throws {
  let o = try await pmdb(["--show"])
  #expect(!o.succeeded)
  #expect(o.error.contains("'--show' requires at least one trace"))
}

@Test func readsApostrophesOutsideStringsAsSingleCharacters() async throws {
  // An apostrophe doesn't start a string, so the second line is a command of its own.
  let o = try await pmdb([makeTrace().trace], input: "select f(x) # x's value\nselect f(x)\n")
  #expect(o.succeeded)
  #expect(o.output == "$0 = <1 element(s) in 1 trace(s)>\n$1 = <1 element(s) in 1 trace(s)>")
  #expect(o.error == "")
}

@Test func ignoresQuotesInComments() async throws {
  let input = "select f(x) # don't use \"quotes\nselect f(x)\nselect f(...)\n"
  let o = try await pmdb([makeTrace().trace], input: input)
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    $1 = <1 element(s) in 1 trace(s)>
    $2 = <1 element(s) in 1 trace(s)>
    """)
}

@Test func readsQuotesOnContinuedLines() async throws {
  // The string on the continued line is closed, so the next line is a command of its own.
  let input = "select f(x) where \\\n\"a\" == \"a\"\nselect f(x)\n"
  let o = try await pmdb([makeTrace().trace], input: input)
  #expect(o.succeeded)
  #expect(o.output == "$0 = <1 element(s) in 1 trace(s)>\n$1 = <1 element(s) in 1 trace(s)>")
  #expect(o.error == "")
}

@Test func endsCommandsInUnterminatedStrings() async throws {
  // String literals can't span lines, so the unterminated string doesn't swallow the next line.
  let o = try await pmdb([makeTrace().trace], input: "select f(x) where \"a\\\"\nselect f(x)\n")
  #expect(!o.succeeded)
  #expect(o.output == "")
}

@Test func continuesLinesEndingWithBackslash() async throws {
  let input = "select f(x) \\\nwhere x == 1 \\\n# comment \\\nselect f(x)\n"
  let o = try await pmdb([makeTrace().trace], input: input)
  #expect(o.succeeded)
  #expect(o.output == "$0 = <1 element(s) in 1 trace(s)>\n$1 = <1 element(s) in 1 trace(s)>")
  #expect(o.error == "")
}

@Test func reportsErrorsAfterPrecedingOutput() async throws {
  let r = try makeTrace()
  let result = try await run(
    .name("sh"), arguments: ["-c", "\"$0\" \"$1\" 2>&1", pmdbExecutable.path, r.trace],
    environment: .inherit.updating(["TERM": "dumb"]),
    input: .fileDescriptor(
      inputFile("select f(x)\nselect f(x) from $nope\n"), closeAfterSpawningProcess: true),
    output: .string(limit: 1 << 20), error: .discarded)
  #expect(result.standardOutput.normalized == """
    $0 = <1 element(s) in 1 trace(s)>
    error: undefined symbol '$nope'
    """)
}

/// The snap recording that `f` returned 2.
private let resultOfF = """
  <pmdb:snap location="a.py:3" label="f.$result">\
  <pmdb:value><pmdb:integer>2</pmdb:integer></pmdb:value></pmdb:snap>
  """

@Test func showsResultsOfCalls() async throws {
  let r = try makeTrace(following: resultOfF)
  let o = try await pmdb(["--non-brief", r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output.hasPrefix("$0 = <1 element(s) in 1 trace(s)>\n\(r.source):3: call f(1) -> 2\n"))
  #expect(o.error == "")

  let t = try await pmdb(["--show", r.trace])
  #expect(t.output == "* call root()\n└─* call f(1) -> 2")
}

@Test func doesNotColorOutputWrittenToPipes() async throws {
  let result = try await run(
    .path(.init(pmdbExecutable.path)), arguments: [makeTrace().trace],
    environment: .inherit.updating(["TERM": "xterm-256color"]),
    input: .fileDescriptor(inputFile("select f(x)\n"), closeAfterSpawningProcess: true),
    output: .string(limit: 1 << 20), error: .string(limit: 1 << 20))
  #expect(result.standardOutput.normalized == "$0 = <1 element(s) in 1 trace(s)>")
}

@Test func namesItselfPmdb() async throws {
  let o = try await pmdb(["--help"])
  #expect(o.succeeded)
  #expect(o.output.contains("USAGE: pmdb "))
}

@Test func failsToExportUnloadableTrace() async throws {
  let o = try await pmdb(["--export-xml", "missing.trace"])
  #expect(!o.succeeded)
  #expect(o.output == "")
}
