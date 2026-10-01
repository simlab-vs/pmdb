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
  ("f(xs, _) where xs[1][1] == \"a\"", 1),
  ("f(xs, _) where xs[1] == xs[1]", 1),
  ("f(xs, t) where xs[1] != t.b", 1),
  ("f(xs, t) where t.len() == 2 && t.a.len() == 1 && t.b.len() == 0", 1),
  ("f(xs, _) where xs.count(x => x == none) == 0 && xs.any(x => x != none)", 1),
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

@Test func selectsCallsWhoseArgumentsAllSatisfyPredicate() async throws {
  // The example given in the README.
  let trace = try await record(
    """
    @r.record
    def f(*xs):
      return 0

    f()
    f(0, 0)
    f(0, 1)
    """)

  var engine = Engine()
  engine.add(trace)
  let result = try await engine.select(query("select f(xs*) where xs.all(x => x == 0)"))
  #expect(result.calls(in: 0).map({ (i) in trace[at: i].description }) == [
    "call f()", "call f(0, 0)",
  ])
}

@Test func readsNoneFromBinaryTrace() async throws {
  let trace = try await record(
    """
    @r.record
    def f(x, y=None):
      pass

    f(None, y=[None, 1])
    """)

  #expect(trace.calls[1].value.positional == [.null])
  #expect(trace.calls[1].value.named["y"] == .array([.null, .integer(1)]))
  #expect(trace.snaps.map(\.value.value) == [.null])
  #expect(trace.snaps[0].value.description == "snap f.$result = none")
}

@Test(arguments: [
  ("f(x) where x == none", 1),
  ("f(x) where x != none", 3),
  ("f(x) where !x", 2),
  ("f(x) where x", 2),
  ("f(x, x)", 0),
  ("g(x, x)", 1),
  ("/.*\\$result/", 5),
])
func selectsNone(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(x):
      return x

    @r.record
    def g(x, y):
      return 0

    f(None)
    f(0)
    f("a")
    f([None])
    g(None, None)
    """)

  var engine = Engine()
  engine.add(trace)
  #expect(try await engine.select(query("select \(source)")).count == count)
}

/// Returns `true` iff `a` and `b` have the same identity and observations.
private func haveSameContents(_ a: Trace, _ b: Trace) -> Bool {
  (a.identity == b.identity)
    && a.snaps.map(\.index) == b.snaps.map(\.index)
    && a.calls.map(\.index) == b.calls.map(\.index)
    && a.snaps.map(\.value.location) == b.snaps.map(\.value.location)
    && a.snaps.map(\.value.label) == b.snaps.map(\.value.label)
    && a.snaps.map(\.value.value) == b.snaps.map(\.value.value)
    && a.calls.map(\.value.location) == b.calls.map(\.value.location)
    && a.calls.map(\.value.function) == b.calls.map(\.value.function)
    && a.calls.map(\.value.positional) == b.calls.map(\.value.positional)
    && a.calls.map(\.value.named) == b.calls.map(\.value.named)
    && a.calls.map(\.value.children) == b.calls.map(\.value.children)
}

@Test func exportsBinaryTraceToXML() async throws {
  let trace = try await record(
    """
    import threading

    class Point:
      def __init__(self, x):
        self.x = x

    @r.record
    def f(*args, **kwargs):
      return None

    @r.record
    def g(x):
      f(x, y=[x])
      raise ValueError(x)

    f(None, -2**63, 2**63 - 1, 2**64, 0.1, -0.0, 1e300, float("inf"), float("-inf"))
    f("", " a ", "x\\r\\ny", "<&>\\"'", "tab\\t", "é😀", "]]>")
    f([], [None, [1]], {}, {"a": {"b": 2}, "<": "&"}, f, Point(1), threading.Lock())
    f(**{"a b": 1, "\\n": 2, "é": 3})
    try:
      g("x")
    except ValueError:
      pass
    r.snapshot("\\t", 1)
    """)

  let xml = try trace.xml()
  let reloaded = try #require(Trace(xml: xml), "\(String(decoding: xml, as: UTF8.self))")
  #expect(haveSameContents(trace, reloaded))
  #expect(reloaded.description == trace.description)

  // Whitespace in attribute values is escaped, since XML parsers replace it with spaces.
  let text = String(decoding: xml, as: UTF8.self)
  #expect(text.contains("label=\"&#9;\"") && text.contains("label=\"&#10;\""))
}

@Test func exportsNaNToXML() async throws {
  let trace = try await record("r.snapshot('x', float('nan'))")
  let reloaded = try #require(Trace(xml: trace.xml()))
  guard case .float(let v) = reloaded.snaps[0].value.value, v.isNaN else {
    Issue.record("expected NaN, got \(reloaded.snaps[0].value.value)")
    return
  }
}

@Test(arguments: ["r.snapshot('x', '\\x01')", "r.snapshot('\\x00', 1)"])
func rejectsCharactersNotRepresentableInXML(program: String) async throws {
  let trace = try await record(program)
  #expect(throws: RuntimeError.self) { try trace.xml() }
}

@Test func readsObjectsThatDoNotOptInAsObjects() async throws {
  let trace = try await record(
    """
    import dataclasses

    class Point:
      def __init__(self, x):
        self.x = x

    @dataclasses.dataclass
    class Frozen:
      x: int

    r.snapshot('point', Point(1))
    r.snapshot('frozen', Frozen(1))
    """)

  for s in trace.snaps {
    guard case .object = s.value.value else {
      Issue.record("expected an object, got \(s.value.value)")
      return
    }
  }
}

@Test func readsNamedTuplesAndEnumerationsFromBinaryTrace() async throws {
  let trace = try await record(
    """
    import collections, enum

    Pair = collections.namedtuple("Pair", ["first", "second"])

    class Color(enum.Enum):
      RED = 1

    r.snapshot('pair', Pair(1, [2]))
    r.snapshot('color', Color.RED)
    r.snapshot('path', __import__("pathlib").PurePosixPath("/a"))
    """)

  #expect(
    trace.snaps[0].value.value == .table(["first": .integer(1), "second": .array([.integer(2)])]))
  #expect(trace.snaps[1].value.value == .string("RED"))

  // Objects of the standard library are pickled.
  guard case .object = trace.snaps[2].value.value else {
    Issue.record("expected an object, got \(trace.snaps[2].value.value)")
    return
  }
}

@Test func readsObjectsConvertedByTheirTypes() async throws {
  let trace = try await record(
    """
    import fractions

    class Celsius:
      def __init__(self, degrees):
        self.degrees = degrees
      def __pmdb__(self):
        return f"{self.degrees}°C"

    class Recursive:
      def __pmdb__(self):
        return self

    recorder.register(
      fractions.Fraction, lambda f: {"numerator": f.numerator, "denominator": f.denominator})

    r.snapshot('temperature', Celsius(20))
    r.snapshot('fraction', fractions.Fraction(1, 3))
    r.snapshot('recursive', Recursive())
    """)

  #expect(trace.snaps[0].value.value == .string("20°C"))
  #expect(
    trace.snaps[1].value.value == .table(["numerator": .integer(1), "denominator": .integer(3)]))
  guard case .object = trace.snaps[2].value.value else {
    Issue.record("expected an object, got \(trace.snaps[2].value.value)")
    return
  }
}

@Test(arguments: [
  ("f(p) where p.x > 1", 1),
  ("f(p) where p.y == none", 2),
  ("g(s) where s.`$variant` == \"Circle\" && s.radius > 1", 1),
])
func selectsObjectsByAttributes(source: String, count: Int) async throws {
  let trace = try await record(
    """
    class Point:
      def __init__(self, x):
        self.x = x
        self.y = None
      def __pmdb__(self):
        return {"x": self.x, "y": self.y}

    @r.record
    def f(p):
      return 0

    @r.record
    def g(s):
      return 0

    f(Point(1))
    f(Point(2))

    # Enums with fields are recorded like this by the Rust recorder.
    g({"$variant": "Circle", "radius": 2})
    g({"$variant": "Square", "side": 3})
    """)

  var engine = Engine()
  engine.add(trace)
  #expect(try await engine.select(query("select \(source)")).count == count)
}
