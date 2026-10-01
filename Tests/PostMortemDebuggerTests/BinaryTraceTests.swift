import Foundation
import Subprocess
import Testing
@testable import PostMortemDebugger

/// Returns the trace recorded by the Python recorder (see `Python/recorder`) while running
/// `program`.
///
/// `program` is Python code having access to a recorder named `r`.
private func record(_ program: String) async throws -> Trace {
  let source = """
    import sys, recorder
    r = recorder.Recorder()
    \(program)
    sys.stdout.buffer.write(r.serialize().buffer)
    """

  #if os(Windows)
    let python = "python"
  #else
    let python = "python3"
  #endif

  let result = try await run(
    .name(python),
    arguments: ["-c", source],
    environment: .inherit.updating(
      ["PYTHONPATH": pythonDirectory.path, "PYTHONDONTWRITEBYTECODE": "1"]),
    output: .bytes(limit: 1 << 20),
    error: .string(limit: 1 << 16))

  if !result.terminationStatus.isSuccess {
    throw RuntimeError(
      "Python recorder failed (\(result.terminationStatus)):\n\(result.standardError ?? "")")
  }
  return try Trace(archive: result.standardOutput)
}

/// The directory containing the Python recorder package.
private let pythonDirectory = URL(fileURLWithPath: #filePath)
  .deletingLastPathComponent()
  .deletingLastPathComponent()
  .deletingLastPathComponent()
  .appendingPathComponent("Python")

@Test func readsNamedArgumentsFromBinaryTrace() async throws {
  let trace = try await record(
    """
    @r.record
    def f(x, a, b):
      return 0
    f(1, a=2, b="x")
    """)

  #expect(trace.calls.map(\.value.function) == ["root", "f"])

  let call = trace.calls[1].value
  #expect(call.positional == [.integer(1)])
  #expect(call.named["a"] == .integer(2))
  #expect(call.named["b"] == .string("x"))
  #expect(call.description == "call f(1, a: 2, b: x)")
}

@Test(arguments: [0.0, 3.14, -2.5, 1e300, .infinity])
func readsFloatsFromBinaryTrace(value: Double) async throws {
  let trace = try await record(
    """
    @r.record
    def f(x, y):
      return x

    v = float("\(value)")
    f(v, y=v)
    """)

  #expect(trace.calls.map(\.value.function) == ["root", "f"])
  #expect(trace.calls[1].value.positional == [.float(value)])
  #expect(trace.calls[1].value.named["y"] == .float(value))
  #expect(trace.snaps[0].value.value == .float(value))
}

@Test func readsFloatFollowedByOtherValues() async throws {
  // A float must consume exactly 8 bytes for the values after it to be read correctly.
  let trace = try await record(
    """
    @r.record
    def f(x, y):
      return 0

    f(1.5, -7)
    """)
  #expect(trace.calls.map(\.value.function) == ["root", "f"])
  #expect(trace.calls[1].value.positional == [.float(1.5), .integer(-7)])
}

@Test(arguments: [Int64.min, -1, 0, 63, 64, Int64.max])
func readsIntegerBoundariesFromBinaryTrace(value: Int64) async throws {
  let trace = try await record("r.snapshot('x', \(value))")
  #expect(trace.calls.map(\.value.function) == ["root"])
  #expect(trace.snaps[0].value.value == .integer(value))
}

@Test(arguments: ["2**63", "-2**63 - 1"])
func readsIntegersOutOfRangeAsObjects(value: String) async throws {
  let trace = try await record("r.snapshot('x', \(value))")
  #expect(trace.calls.map(\.value.function) == ["root"])
  guard case .object = trace.snaps[0].value.value else {
    Issue.record("expected an object, got \(trace.snaps[0].value.value)")
    return
  }
}

@Test func selectsCallsWithNamedArgumentsFromBinaryTrace() async throws {
  let trace = try await record(
    """
    @r.record
    def f(x=0, a=0):
      return 0

    f(a=1)
    f(a=2)
    f(0.5)
    """)
  #expect(trace.calls.map(\.value.function) == ["root", "f", "f", "f"])

  var engine = Engine()
  engine.add(trace)
  let named = try await engine.select(query("select f(a = x) where x > 1"))
  #expect(named.count == 1)
  let floats = try await engine.select(query("select f(x) where x < 1.0"))
  #expect(floats.count == 1)
}
