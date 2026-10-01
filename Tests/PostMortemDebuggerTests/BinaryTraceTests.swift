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

@Test(arguments: ["r.parent[0] = 1", "r.parent[1] = 1", "r.parent[1] = 5", "r.parent[2] = 2"])
func rejectsInvalidParents(mutation: String) async throws {
  await #expect(throws: (any Error).self) {
    try await record(
      """
      @r.record
      def f():
        return 0
      f()
      \(mutation)
      """)
  }
}

@Test func recordsCallsAfterException() async throws {
  let trace = try await record(
    """
    @r.record
    def bad():
      raise ValueError()

    @r.record
    def h():
      try:
        bad()
      except ValueError:
        pass
      return 0

    h()
    r.snapshot('x', 1)
    """)

  let expected = """
    * call root()
    ├─* call h()
    │ ├─* call bad()
    │ └─* snap bad.$exception = {message: , type: ValueError}
    ├─* snap h.$result = 0
    └─* snap x = 1

    """
  #expect(trace.description == expected)
}

@Test func recordsNameOfRecordedFunctionArgument() async throws {
  let trace = try await record(
    """
    @r.record
    def inc(x):
      return x + 1

    @r.record
    def ap(f, x):
      return f(x)

    ap(inc, 1)
    """)
  #expect(trace.calls[1].value.positional == [.function("inc"), .integer(1)])
}

@Test func readsArraysAndTablesFromBinaryTrace() async throws {
  let trace = try await record(
    """
    @r.record
    def f(xs, t):
      return 0

    f([1, (2.5, "a")], {"b": [], "a": {"c": 3}})
    """)

  let call = trace.calls[1].value
  #expect(call.positional == [
    .array([.integer(1), .array([.float(2.5), .string("a")])]),
    .table(["a": .table(["c": .integer(3)]), "b": .array([])]),
  ])
  #expect(call.description == "call f([1, [2.5, a]], {a: {c: 3}, b: []})")
}

@Test func readsSelfReferentialArrayAsObject() async throws {
  let trace = try await record(
    """
    xs = [1]
    xs.append(xs)
    r.snapshot('xs', xs)
    """)

  guard case .array(let xs) = trace.snaps[0].value.value, xs.count == 2, case .object = xs[1]
  else {
    Issue.record("expected an array ending with an object, got \(trace.snaps[0].value.value)")
    return
  }
  #expect(xs[0] == .integer(1))
}

@Test func readsTablesWithNonStringKeysAsObjects() async throws {
  let trace = try await record("r.snapshot('t', {1: 2})")
  guard case .object = trace.snaps[0].value.value else {
    Issue.record("expected an object, got \(trace.snaps[0].value.value)")
    return
  }
}

@Test(arguments: [
  ("f(xs, _) where xs[0] == 1", 1),
  ("f(xs, _) where xs[1][0] > 2.0", 1),
  ("f(_, t) where t.a.c == 3", 1),
  ("f(_, t) where t.b", 0),
])
func selectsCallsByArrayAndTableContents(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(xs, t):
      return 0

    f([1, (2.5, "a")], {"b": [], "a": {"c": 3}})
    """)

  var engine = Engine()
  engine.add(trace)
  #expect(try await engine.select(query("select \(source)")).count == count)
}

@Test func recordsValuesAsTheyWereWhenObserved() async throws {
  let trace = try await record(
    """
    @r.record
    def append(xs, x):
      xs.append(x)
      return xs

    xs = []
    append(xs, 1)
    append(xs=xs, x=2)
    r.snapshot('xs', xs)
    xs.append(3)
    """)

  #expect(trace.calls[1].value.positional == [.array([]), .integer(1)])
  #expect(trace.calls[2].value.named["xs"] == .array([.integer(1)]))
  #expect(trace.snaps.map(\.value.value) == [
    .array([.integer(1)]),
    .array([.integer(1), .integer(2)]),
    .array([.integer(1), .integer(2)]),
  ])
}

@Test func recordsDescriptionsOfUnpicklableValues() async throws {
  let trace = try await record(
    """
    import threading

    @r.record
    def f(x):
      return threading.Lock()

    @r.record
    async def g():
      return 0

    class Opaque:
      def __reduce__(self):
        raise TypeError()
      def __repr__(self):
        raise TypeError()

    f(x for x in [])
    g().close()
    r.snapshot('x', Opaque())
    """)

  let values = [trace.calls[1].value.positional[0]] + trace.snaps.map(\.value.value)
  let descriptions = values.map { (v) -> String? in
    if case .string(let s) = v { s } else { nil }
  }
  #expect(descriptions[0]?.hasPrefix("<generator object") ?? false)
  #expect(descriptions[1]?.hasPrefix("<unlocked _thread.lock object") ?? false)
  #expect(descriptions[2]?.hasPrefix("<coroutine object") ?? false)
  #expect(descriptions[3] == "<Opaque object>")
}

@Test func recordsExceptions() async throws {
  let trace = try await record(
    """
    @r.record
    def bad(x):
      raise KeyError(x)

    @r.record
    def h():
      bad("k")

    try:
      h()
    except KeyError:
      pass
    """)

  let expected = """
    * call root()
    ├─* call h()
    │ ├─* call bad(k)
    │ └─* snap bad.$exception = {message: 'k', type: KeyError}
    └─* snap h.$exception = {message: 'k', type: KeyError}

    """
  #expect(trace.description == expected)

  var engine = Engine()
  engine.add(trace)
  let raised = try await engine.select(query("select /.*\\$exception/"))
  #expect(raised.count == 2)
}
