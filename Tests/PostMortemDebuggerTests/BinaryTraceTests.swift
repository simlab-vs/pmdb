import BigInt
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

// Signed LEB128 encodes integers in [-2^62, 2^62) with at most 9 bytes, and others with more.
@Test(arguments: [
  Int64.min, -1, 0, 63, 64, Int64.max,
  0x4000_0000_0000_0000, 0x3fff_ffff_ffff_ffff, -0x4000_0000_0000_0000, -0x4000_0000_0000_0001,
] as [Int64])
func readsIntegerBoundariesFromBinaryTrace(value: Int64) async throws {
  let trace = try await record("r.snapshot('x', \(value))")
  #expect(trace.calls.map(\.value.function) == ["root"])
  #expect(trace.snaps[0].value.value == .integer(BigInt(value)))
}

@Test(arguments: [
  ("2**63", "9223372036854775808"),
  ("-2**63 - 1", "-9223372036854775809"),
  ("10**40", "10000000000000000000000000000000000000000"),
  ("-10**40", "-10000000000000000000000000000000000000000"),
])
func readsWideIntegersFromBinaryTrace(value: String, digits: String) async throws {
  let trace = try await record("r.snapshot('x', \(value))")
  #expect(trace.calls.map(\.value.function) == ["root"])
  #expect(trace.snaps[0].value.value == .integer(BigInt(digits)!))
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
    ├─* call h() -> 0
    │ └─* call bad() raised {message: , type: ValueError}
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

@Test func doesNotRecordCallsMadeWhileEncodingValues() async throws {
  // `isinstance` reads `__class__`, and describing an unpicklable object calls `__repr__`: if
  // these calls were recorded, recording them would encode the same objects again, forever.
  let trace = try await record(
    """
    import threading

    class Proxy:
      def __init__(self):
        self.lock = threading.Lock()

      @property
      @r.record
      def __class__(self):
        return Proxy

      @r.record
      def __repr__(self):
        return "proxy"

    @r.record
    def f(x):
      return 1

    f(Proxy())
    """)

  let expected = """
    * call root()
    └─* call f(proxy) -> 1

    """
  #expect(trace.description == expected)
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
    └─* call h() raised {message: 'k', type: KeyError}
      └─* call bad(k) raised {message: 'k', type: KeyError}

    """
  #expect(trace.description == expected)

  var engine = Engine()
  engine.add(trace)
  let raised = try await engine.select(query("select /.*\\$exception/"))
  #expect(raised.count == 2)

  // Calls that raised don't return values.
  let returned = try await engine.select(query("select _(...) -> _"))
  #expect(returned.count == 0)
}

@Test(arguments: [
  ("_(...) raised _", 2),
  ("_(...) -> _", 1),
  ("_(...)", 4),  // Including the root, which neither returned nor raised.
  ("bad(x) raised e where e.type == \"KeyError\" && x == \"k\"", 1),
  ("h() raised e where e.message == \"'k'\"", 1),
  ("_(...) raised e where e.type == \"ValueError\"", 0),
  ("ok(raised) -> raised", 1),
  ("ok(raised) where raised - 1 == 0", 1),
])
func selectsCallsByOutcome(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def bad(x):
      raise KeyError(x)

    @r.record
    def h():
      bad("k")

    @r.record
    def ok(x):
      return x

    try:
      h()
    except KeyError:
      pass
    ok(1)
    """)

  var engine = Engine()
  engine.add(trace)
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}

@Test(arguments: [
  ("f(\"x\")", 1),
  ("f(\"y\", b = -1)", 1),
  ("f(\"y\", b = 1)", 0),
  ("f(2.5, c = false)", 1),
  ("f(2.5, c = 0)", 0),
  ("f(_, b = none)", 1),
  ("f(a) -> \"x\"", 1),
  ("f(a, **) -> 2.5", 1),
])
func matchesLiteralPatterns(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(a, b=None, c=True):
      return a

    f("x")
    f("y", b=-1)
    f(2.5, c=False)
    f("z", b=None)
    """)
  var engine = Engine()
  engine.add(trace)
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}

@Test(arguments: [
  ("g(*, _)", 2),
  ("g(*, 3)", 1),
  ("g(*, 2)", 0),
  ("g(1, *, 3)", 1),
  ("g(_, *, _)", 1),
  ("g(*, _, *)", 2),
  ("g(*, *)", 3),
  ("g(xs*, x) where xs.len() == 2 && x == 3", 1),
  ("g(xs*, ys*) where xs.len() == 3 && ys.len() == 0", 1),
  ("g(**, k = 2)", 0),
  ("g(_, **, k = 2)", 1),
  ("g(_, kw**, k = x) where kw.len() == 0 && x == 2", 1),
  ("g(*, k = 2, **)", 1),
])
func matchesVariadicPatternsAnywhere(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def g(*args, **kwargs):
      return 0

    g(1, 2, 3)
    g(1)
    g()
    g(1, k=2)
    """)
  var engine = Engine()
  engine.add(trace)
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}

@Test(arguments: [
  ("f(o) where o.has(\"coupon\")", 1),
  ("f(o) where !o.has(\"coupon\")", 2),
  ("f(o) where o.has(\"coupon\") && o.coupon == \"BIG50\"", 1),
  ("f(o) where o.has(\"$variant\")", 1),
  ("f(o) where o.has(\"len\")", 0),
  ("f(o) where (k => o.has(k))(\"id\")", 3),
])
func testsWhetherTablesHaveProperties(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(order):
      return 0

    f({"id": 1, "coupon": "BIG50"})
    f({"id": 2})
    f({"id": 3, "$variant": "Some"})
    """)
  var engine = Engine()
  engine.add(trace)
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}

@Test func bindsResultsOfCalls() async throws {
  let trace = try await record(
    """
    @r.record
    def f(x):
      return [x, x * 2]

    f(1)
    f(3)
    """)

  var engine = Engine()
  engine.add(trace)
  let large = try await engine.select(query("select f(x) -> r where r[1] > 4"))
  #expect(large.count == 1)
  let consistent = try await engine.select(query("select f(x) -> r where r[0] == x"))
  #expect(consistent.count == 2)
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

@Test func readsBooleansFromBinaryTrace() async throws {
  let trace = try await record(
    """
    @r.record
    def f(x, y=None):
      return x

    f(True, y=[False, 1])
    """)

  #expect(trace.calls[1].value.positional == [.boolean(true)])
  #expect(trace.calls[1].value.named["y"] == .array([.boolean(false), .integer(1)]))
  #expect(trace.snaps[0].value.description == "snap f.$result = true")
}

@Test(arguments: [(1, true), (2, false)])
func readsOnlyZeroOrOneAsBooleans(payload: Int, isValid: Bool) async throws {
  let program = """
    r.snapshot("x", True)
    r.observations[1].value = bytes([0x06, \(payload)])
    """
  if isValid {
    let trace = try await record(program)
    #expect(trace.snaps.map(\.value.value) == [.boolean(true)])
  } else {
    await #expect(throws: (any Error).self) { try await record(program) }
  }
}

@Test(arguments: [
  ("f(x) where x == true", 1),
  ("f(x) where x == false", 1),
  ("f(x) where x", 1),
  ("f(x) where x & true", 1),
])
func selectsBooleans(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(x):
      pass

    f(True)
    f(False)
    """)

  var engine = Engine()
  engine.add(trace)
  #expect(try await engine.select(query("select \(source)")).count == count)
}

@Test(arguments: [
  ("f(0)", 3),
  ("f(0.0)", 3),
  ("f(x) where x == 0", 3),
  ("f(x) where x < 0.5", 3),
  ("f(x) where x < 1", 4),
  ("f(x) where x >= 1", 3),
  ("f(x) where !(x < 1) && !(x >= 1)", 1),
  ("f(x) where x == x", 7),
  ("f(x) where x != x", 1),
  ("f(x) where bool(x)", 4),
  ("f(x) where x == 9007199254740993", 1),
  ("f(x) where x > 9007199254740992.0", 2),
  ("f(9007199254740992)", 1),
  ("g(xs, t, ys, u) where xs == ys && t == u", 1),
  ("h(x, x)", 1),
])
func comparesNumbersByValue(source: String, count: Int) async throws {
  let trace = try await record(
    """
    @r.record
    def f(x):
      pass

    @r.record
    def g(xs, t, ys, u):
      pass

    @r.record
    def h(x, y):
      pass

    for x in [0, 0.0, -0.0, 0.5, float("nan"), 2**53 + 1, 2.0**53, float("inf")]:
      f(x)
    g([0, 1.0], {"a": 1}, [0.0, 1], {"a": 1.0})
    h(0, 0.0)
    h(float("nan"), float("nan"))
    """)

  var engine = Engine()
  engine.add(trace)
  #expect(try await engine.select(query("select \(source)")).count == count)
}

@Test(arguments: [
  ("f(x) where x == none", 1),
  ("f(x) where x != none", 3),
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

    f(None, True, False, -2**63, 2**63 - 1, 2**64, 0.1, -0.0, 1e300, float("inf"), float("-inf"))
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
