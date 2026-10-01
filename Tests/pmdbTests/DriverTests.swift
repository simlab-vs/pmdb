import Foundation
import Subprocess
import Testing

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

/// Returns the outcome of running `pmdb` with `arguments`, feeding `input` to its standard input,
/// or throws `Timeout` if it does not exit within `timeLimit`.
///
/// The output and the error are normalized; see `String.normalized`.
private func pmdb(_ arguments: [String] = [], input: String = "") async throws -> Outcome {
  try await withThrowingTaskGroup(of: Outcome.self) { (group) in
    group.addTask {
      let result = try await run(
        .path(.init(pmdbExecutable.path)),
        arguments: .init(arguments),
        environment: .inherit.updating(["TERM": "dumb"]),
        input: .string(input),
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

/// Writes `source` and a trace with one call to `f` at `line` of `source` in a fresh directory.
private func makeTrace(
  source: String = "def f(x):\n  return x\nf(1)\n", callingAt line: Int = 3
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
  #expect(o.output == "(pmdb) $0 = <1 element(s) in 1 trace(s)>\n(pmdb)")
  #expect(o.error == "")
}

@Test func exitsAtEndOfInput() async throws {
  let o = try await pmdb()
  #expect(o.succeeded)
  #expect(o.output == "(pmdb)")
  #expect(o.error == "")
}

@Test func reportsQueryErrors() async throws {
  let o = try await pmdb([makeTrace().trace], input: "select f(x) from $nope\nselect f(x)\n")
  #expect(o.succeeded)
  #expect(o.output == "(pmdb) (pmdb) $0 = <1 element(s) in 1 trace(s)>\n(pmdb)")
  #expect(o.error == "error: undefined symbol '$nope'")
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
  let o = try await pmdb([r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    (pmdb) $0 = <1 element(s) in 1 trace(s)>
    (pmdb) \(r.source):\(line): call f(1)
    \(excerpt)
    continue? [Y/n] (pmdb)
    """)
  #expect(o.error == "")
}

@Test func showsObservationPastEndOfSource() async throws {
  let r = try makeTrace(source: sevenLines, callingAt: 10)
  let o = try await pmdb([r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    (pmdb) $0 = <1 element(s) in 1 trace(s)>
    (pmdb) \(r.source):10: call f(1)
    continue? [Y/n] (pmdb)
    """)
  #expect(o.error == "")
}

@Test func showsLastLineWithoutLineSeparator() async throws {
  let r = try makeTrace(source: "a\nb", callingAt: 2)
  let o = try await pmdb([r.trace], input: "select f(x)\nshow $0\n")
  #expect(o.succeeded)
  #expect(o.output == """
    (pmdb) $0 = <1 element(s) in 1 trace(s)>
    (pmdb) \(r.source):2: call f(1)
         1 | a
    >    2 | b
    continue? [Y/n] (pmdb)
    """)
  #expect(o.error == "")
}

@Test func executesQuery() async throws {
  let r = try makeTrace()
  let o = try await pmdb([r.trace, "-e", "select f(x)"])
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):3: call f(1)
    """)
  #expect(o.error == "")
}

@Test func executesCommandsInOrder() async throws {
  let r = try makeTrace()
  let o = try await pmdb([
    r.trace, "-e", "select f(x)", "-e", "select _(...) from $0", "-e", "show $1",
  ])
  #expect(o.succeeded)
  #expect(o.output == """
    $0 = <1 element(s) in 1 trace(s)>
    \(r.source):3: call f(1)
    $1 = <1 element(s) in 1 trace(s)>
    \(r.source):3: call f(1)
    \(r.source):3: call f(1)
         1 | def f(x):
         2 |   return x
    >    3 | f(1)
    """)
  #expect(o.error == "")
}

@Test func stopsAtFirstFailingCommand() async throws {
  let o = try await pmdb([makeTrace().trace, "-e", "select f(x) from $nope", "-e", "select f(x)"])
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: undefined symbol '$nope'")
}

@Test func rejectsTrailingInput() async throws {
  let o = try await pmdb([makeTrace().trace, "-e", "select f(x) )"])
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: multiple commands should be separated by a newline")
}

@Test func exitStopsExecution() async throws {
  let o = try await pmdb([makeTrace().trace, "-e", "exit", "-e", "select f(x)"])
  #expect(o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "")
}

@Test func failsOnUnloadableTrace() async throws {
  let o = try await pmdb(["missing.trace", "-e", "select f(x)"])
  #expect(!o.succeeded)
  #expect(o.output == "")
}

@Test func reportsEvaluationErrors() async throws {
  let o = try await pmdb([makeTrace().trace, "-e", "select f(x) where x.y"])
  #expect(!o.succeeded)
  #expect(o.output == "")
  #expect(o.error == "error: value of type 'integer' is not a table")
}
