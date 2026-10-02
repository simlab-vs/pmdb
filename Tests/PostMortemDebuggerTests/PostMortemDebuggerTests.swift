import Foundation
import Testing
@testable import PostMortemDebugger

/// A trace of `factorial(3)`:
/// 
// import recorder as pmdb

/// @pmdb.main.record
/// def factorial(n):
///   return 1 if n < 2 else n * factorial(n - 1)
///
/// if __name__ == "__main__":
///   n = pmdb.main.run(factorial, 3)
///   print(n)  # Prints 6
///
///   with open("factorial.trace", "wb") as f:
///     archive = pmdb.main.serialize()
/// @pmdb.main.record
/// def factorial(n):
///   return 1 if n < 2 else n * factorial(n - 1)
///
/// if __name__ == "__main__":
///   n = pmdb.main.run(factorial, 3)
///   print(n)  # Prints 6
///
///   with open("factorial.trace", "wb") as f:
///     archive = pmdb.main.serialize()
///     f.write(archive.buffer)

private let factorialTrace = """
  <?xml version="1.0" encoding="UTF-8"?>
  <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
    <pmdb:observations>
      <pmdb:call location="factorial.py:8">
        <pmdb:function>root</pmdb:function>
        <pmdb:arguments/>
        <pmdb:observations>
          <pmdb:call location="factorial.py:8">
            <pmdb:function>factorial</pmdb:function>
            <pmdb:arguments><pmdb:value><pmdb:integer>3</pmdb:integer></pmdb:value></pmdb:arguments>
            <pmdb:observations>
              <pmdb:call location="factorial.py:5">
                <pmdb:function>factorial</pmdb:function>
                <pmdb:arguments><pmdb:value><pmdb:integer>2</pmdb:integer></pmdb:value></pmdb:arguments>
                <pmdb:observations>
                  <pmdb:call location="factorial.py:5">
                    <pmdb:function>factorial</pmdb:function>
                    <pmdb:arguments><pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value></pmdb:arguments>
                  </pmdb:call>
                  <pmdb:snap location="factorial.py:5" label="factorial.$result">
                    <pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value>
                  </pmdb:snap>
                </pmdb:observations>
              </pmdb:call>
              <pmdb:snap location="factorial.py:5" label="factorial.$result">
                <pmdb:value><pmdb:integer>2</pmdb:integer></pmdb:value>
              </pmdb:snap>
            </pmdb:observations>
          </pmdb:call>
          <pmdb:snap location="factorial.py:5" label="factorial.$result">
            <pmdb:value><pmdb:integer>6</pmdb:integer></pmdb:value>
          </pmdb:snap>
        </pmdb:observations>
      </pmdb:call>
    </pmdb:observations>
  </pmdb:trace>
  """

/// Returns the trace in `factorialTrace`.
private func loadFactorialTrace() throws -> Trace {
  try #require(Trace(xml: Data(factorialTrace.utf8)))
}

/// Returns the query parsed from `source`.
func query(_ source: String) throws -> Query {
  var parser = Parser(source)
  let command = try parser.parseCommand()
  #expect(parser.diagnostics.isEmpty)
  guard case .select(let q) = command else {
    Issue.record("expected a select command, got \(command)")
    throw RuntimeError("not a query")
  }
  return q
}

@Test func parsesXMLTrace() throws {
  let trace = try loadFactorialTrace()
  #expect(trace.calls.map(\.value.function) == ["root", "factorial", "factorial", "factorial"])
  #expect(trace.snaps.map(\.value.value) == [.integer(1), .integer(2), .integer(6)])
  #expect(trace.snaps.allSatisfy { $0.value.label == "factorial.$result" })
  #expect(trace.calls[1].value.positional == [.integer(3)])
  #expect(trace.calls[1].value.location == SourceLine(8, in: "factorial.py"))

  let expected = """
    * call root()
    └─* call factorial(3) -> 6
      └─* call factorial(2) -> 2
        └─* call factorial(1) -> 1

    """
  #expect(trace.description == expected)
}

@Test func findsOutcomesOfCalls() throws {
  let trace = try loadFactorialTrace()
  let outcomes = trace.calls.map({ (c) -> Value? in
    if case .returned(let v) = trace.outcome(of: c.index) { v } else { nil }
  })
  #expect(outcomes == [nil, .integer(6), .integer(2), .integer(1)])
  #expect(trace.description(of: trace.calls[1].index) == "call factorial(3) -> 6")
  #expect(trace.description(of: trace.calls[0].index) == "call root()")
}

@Test func ignoresSnapsOfOtherFunctionsAsOutcomes() throws {
  let source = """
    <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
      <pmdb:observations>
        <pmdb:call location="a.py:1">
          <pmdb:function>root</pmdb:function>
          <pmdb:arguments/>
          <pmdb:observations>
            <pmdb:call location="a.py:1"><pmdb:function>f</pmdb:function><pmdb:arguments/></pmdb:call>
            <pmdb:snap location="a.py:1" label="g.$result">
              <pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value>
            </pmdb:snap>
          </pmdb:observations>
        </pmdb:call>
      </pmdb:observations>
    </pmdb:trace>
    """
  let trace = try #require(Trace(xml: Data(source.utf8)))
  #expect(trace.outcome(of: trace.calls[1].index) == nil)
  #expect(trace.description == "* call root()\n├─* call f()\n└─* snap g.$result = 1\n")
}

@Test func describesLiteralPatterns() {
  let xs = ArgumentPatternList([
    .positionalLiteral(.string("a\"b\n")), .positionalLiteral(.float(2.5)),
    .namedLiteral(label: "k", value: .integer(-1)), .namedLiteral(label: "n", value: .null),
  ])
  #expect(xs.description == "\"a\\\"b\\n\", 2.5, k = -1, n = none")
}

@Test func requiresPatternAfterArrow() {
  var parser = Parser("select f(x) ->")
  #expect(throws: Diagnostic.self) { try parser.parseCommand() }
}

@Test func rejectsXMLTraceWithManyRoots() {
  let source = """
    <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
      <pmdb:observations>
        <pmdb:snap location="a.py:1"><pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value></pmdb:snap>
        <pmdb:snap location="a.py:2"><pmdb:value><pmdb:integer>2</pmdb:integer></pmdb:value></pmdb:snap>
      </pmdb:observations>
    </pmdb:trace>
    """
  #expect(Trace(xml: Data(source.utf8)) == nil)
}

@Test func parsesArraysAndTablesInXMLTrace() throws {
  let source = """
    <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
      <pmdb:observations>
        <pmdb:snap location="a.py:1" label="x">
          <pmdb:value>
            <pmdb:array>
              <pmdb:value>
                <pmdb:integer>42</pmdb:integer>
              </pmdb:value>
              <pmdb:value>
                <pmdb:table>
                  <pmdb:value label="b"><pmdb:string>s</pmdb:string></pmdb:value>
                  <pmdb:value label="a"><pmdb:array/></pmdb:value>
                  <pmdb:value label="c"><pmdb:none/></pmdb:value>
                </pmdb:table>
              </pmdb:value>
            </pmdb:array>
          </pmdb:value>
        </pmdb:snap>
      </pmdb:observations>
    </pmdb:trace>
    """
  let trace = try #require(Trace(xml: Data(source.utf8)))
  #expect(trace.snaps.map(\.value.value) == [
    .array([.integer(42), .table(["a": .array([]), "b": .string("s"), "c": .null])])
  ])
}

@Test(arguments: [
  "<pmdb:table><pmdb:value><pmdb:integer>1</pmdb:integer></pmdb:value></pmdb:table>",
  """
  <pmdb:table>
    <pmdb:value label="a"><pmdb:integer>1</pmdb:integer></pmdb:value>
    <pmdb:value label="a"><pmdb:integer>2</pmdb:integer></pmdb:value>
  </pmdb:table>
  """,
  "<pmdb:array><pmdb:integer>1</pmdb:integer></pmdb:array>",
])
func rejectsInvalidCollectionsInXMLTrace(value: String) {
  #expect(Trace(xml: Data(snapping(value).utf8)) == nil)
}

/// Returns a trace document with a single snap of `value`, a `pmdb:value` payload.
private func snapping(_ value: String) -> String {
  """
  <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
    <pmdb:observations>
      <pmdb:snap location="a.py:1"><pmdb:value>\(value)</pmdb:value></pmdb:snap>
    </pmdb:observations>
  </pmdb:trace>
  """
}

@Test(arguments: [("true", true), ("false", false)])
func parsesBooleansInXMLTrace(payload: String, value: Bool) throws {
  let trace = try #require(Trace(xml: Data(snapping("<pmdb:boolean>\(payload)</pmdb:boolean>").utf8)))
  #expect(trace.snaps.map(\.value.value) == [.boolean(value)])

  let reloaded = try #require(Trace(xml: trace.xml()))
  #expect(reloaded.snaps.map(\.value.value) == [.boolean(value)])
}

@Test(arguments: ["1", "0", "True", ""])
func rejectsInvalidBooleansInXMLTrace(payload: String) {
  #expect(Trace(xml: Data(snapping("<pmdb:boolean>\(payload)</pmdb:boolean>").utf8)) == nil)
}

@Test(arguments: [
  ("factorial(x) where x > 1", 2),
  ("factorial(...)", 3),
  ("_(...)", 4),
  ("/.*\\$result/ where true", 3),
  ("factorial(x) where x > -9223372036854775808", 3),
  ("factorial(x) where x > 4/x", 1),
  ("factorial(x) where x-1 > 1", 1),
  ("factorial(x) where x>-1", 3),
  ("factorial(x) where -1 < x", 3),
  ("factorial(x) where if x > 1 then -1 else 0", 2),
  ("factorial(x) where (x)-1 > 1", 1),
  ("factorial(x) where -x < -1", 2),
  ("factorial(x) where -x == 0 - 3", 1),
  ("factorial(x) where -(x - 1) == 0", 1),
  ("factorial(x) where !(x > 1)", 1),
  ("factorial(x) where !x", 0),
  ("factorial(x) where x && x", 3),
  ("factorial(x) where x > 1 && x < 3", 1),
  ("factorial(x) where x == 1 || x == 3", 2),
  ("factorial(x) where x < 2 || x > 2 && x < 3", 1),
  ("factorial(x) where x > 0 || y", 3),
  ("factorial(x) where x < 0 && y", 0),
  ("factorial(x) where x > 1 && 1 / (x - 1) == 1", 1),
  ("factorial(x) where (x & 1) == 1", 2),
  ("factorial(x) where (x ^ 3) == 1", 1),
  ("factorial(x) where (x | 1) == 3", 2),
  ("factorial(x) where (x&-2) == 2", 2),
  ("factorial(x) where x & 2 == 2", 2),
  ("factorial(x) where x | 4 ^ 1 & 3 == 6", 1),
  ("factorial(x) where x + x & 1 == 4", 1),
  ("factorial(x) where x - 1 | 1 == 1", 2),
  ("factorial(x) where (x > 1) == true", 2),
  ("factorial(x) where (x > 1) != (x > 2)", 1),
  ("factorial(x) where true != false", 3),
  ("factorial(x) where !(x > 1) == true", 1),
  ("factorial(x) where (x > 2) | (x < 2)", 2),
  ("factorial(x) where (x > 1) ^ (x > 2)", 1),
  ("factorial(x) where true & (x > 1)", 2),
  ("factorial(x) where false", 0),
  ("factorial(x) where if x > 1 then false else true", 1),
  ("factorial(x) where \"a\" == \"a\"", 3),
  ("factorial(x) where \"a\" != \"b\"", 3),
  ("factorial(x) where \"a\\\"\" == \"a\"", 0),
  ("factorial(x) where none == none", 3),
  ("factorial(x) where x != none", 3),
  ("factorial(x) where !none", 3),
  ("factorial(x) where -1 == none", 0),
  ("factorial(xs*) where xs.all(x => x > 1)", 2),
  ("factorial(xs*) where xs.all(x => xs[0] == x)", 3),
  ("factorial(xs*) where xs.any(x => x > 2)", 1),
  ("factorial(xs*, ys**) where ys.len() == 0", 3),
  ("factorial(xs*) where xs.len() == 1", 3),
  ("factorial(xs*) where xs.count(x => x > 1) == 1", 2),
  ("factorial(xs*) where xs.count(x => x > 1) + xs.len() == 1", 1),
  ("factorial(x) where (y => y > 1)(x)", 2),
  ("factorial(x) where (y => x == y)(x)", 3),
  ("factorial(x) where (y => z => y == z)(x)(2)", 1),
  ("factorial(x) -> r where r > x", 1),
  ("factorial(x) -> r where r == 2", 1),
  ("factorial(x) -> x", 2),
  ("factorial(_) -> _", 3),
  ("factorial(...) -> r where r == 6", 1),
  ("_(...) -> _", 3),
  ("root() -> _", 0),
  ("factorial(3)", 1),
  ("factorial(3) -> 6", 1),
  ("factorial(x) -> 2", 1),
  ("factorial(-1)", 0),
  ("factorial(3.0)", 1),
  ("factorial(x) where x == 3.0", 1),
  ("factorial(x) where x < 2.5", 2),
  ("factorial(x) where 2.5 <= x", 1),
  ("factorial(\"3\")", 0),
  ("factorial(true)", 0),
  ("factorial(none)", 0),
  ("factorial(3, x)", 0),
  ("factorial(x) where x * 1_000 == 3_000", 1),
  ("factorial(x) where 1_000.5 > 1_000.0", 3),
  ("factorial(-0_1)", 0),
  ("factorial(x) where x + 9223372036854775807 > 9223372036854775807", 3),
  ("factorial(x) where -(x - 9223372036854775807 - 2) == 9223372036854775806", 1),
  ("factorial(x) where x * 99999999999999999999 == 299999999999999999997", 1),
  ("factorial(x) where x + 1.0 > 3", 1),
  ("factorial(x) where x / 2 == 1.5", 1),
  ("factorial(x) where 7 / 2 == 3.5", 3),
  ("factorial(x) where x * 0.5 == 1", 1),
  ("factorial(x) where x - 0.5 > 2", 1),
  ("factorial(x) where 1.5 - x < 0", 2),
  ("factorial(x) where 1152921504606846976 + 0.5 > x", 3),
  ("factorial(x) where (x | 18446744073709551616) == 18446744073709551619", 1),
  ("factorial(x) where (-18446744073709551616 ^ -x) == 18446744073709551613", 1),
])
func selectsObservations(source: String, count: Int) async throws {
  var engine = Engine()
  engine.add(try loadFactorialTrace())
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}

@Test(arguments: [
  ("factorial(x) where -x.y", "value of type 'integer' is not a table"),
  ("factorial(x) where ~x", "unsupported prefix operator '~'"),
  ("factorial(x) where x > 1 || y", "undefined symbol 'y'"),
  ("factorial(x) where x(1)", "value of type 'integer' is not a lambda"),
  ("factorial(x) where x < none", "cannot apply < on values of type 'integer' and 'none'"),
  ("factorial(x) where none + 1", "cannot apply + on values of type 'none' and 'integer'"),
  ("factorial(x) where -none", "cannot apply - on value of type 'none'"),
  ("factorial(x) where (y => y)(1, 2)", "expected 1 argument(s), found 2"),
  ("factorial(xs*) where xs.sum()", "value of type 'array' has no method 'sum'"),
  ("factorial(xs*) where xs.len(1)", "expected 0 argument(s), found 1"),
  ("factorial(xs*) where xs.count()", "expected 1 argument(s), found 0"),
  ("factorial(xs*) where xs.any(x => x.y)", "value of type 'integer' is not a table"),
  ("factorial(x) where (y => y)()", "expected 1 argument(s), found 0"),
  ("factorial(xs*) where xs.all(1)", "value of type 'integer' is not a lambda"),
  ("factorial(xs*) where xs.all(x => x.y)", "value of type 'integer' is not a table"),
  ("factorial(x) where x % 2", "unsupported operation '%'"),
  ("factorial(x) where x | 1.0", "cannot apply | on values of type 'integer' and 'float'"),
  ("factorial(x) where true == 1", "cannot apply == on values of type 'boolean' and 'integer'"),
  ("factorial(x) where (x > 1) + 1", "cannot apply + on values of type 'boolean' and 'integer'"),
  ("factorial(x) where true < false", "cannot apply < on values of type 'boolean' and 'boolean'"),
  ("factorial(x) where -true", "cannot apply - on value of type 'boolean'"),
  ("factorial(x) where true & 1", "cannot apply & on values of type 'boolean' and 'integer'"),
  ("factorial(x) where x > 1 & x < 3", "cannot apply < on values of type 'boolean' and 'integer'"),
  ("factorial(x) where x == \"1\"", "cannot apply == on values of type 'integer' and 'string'"),
  ("factorial(x) where \"\\q\" == \"\"", "invalid escape sequence '\\q'"),
  ("factorial(x) where 1 / (x - 1) > 0", "division by zero in '/'"),
  ("factorial(x) where 1.0 / 0.0 > 0.0", "division by zero in '/'"),
  ("factorial(x) where 9007199254740993 + 0.5 > x", "integer '9007199254740993' has no exact floating-point representation in '+'"),
  ("factorial(x) where 99999999999999999999 / x > 0", "integer '99999999999999999999' has no exact floating-point representation in '/'"),
  ("factorial(x) where x / 0.0 > 0", "division by zero in '/'"),
  ("factorial(x) where x + \"1\" > 0", "cannot apply + on values of type 'integer' and 'string'"),
  ("factorial(x) where y", "undefined symbol 'y'"),
  ("factorial(x) where x.y", "value of type 'integer' is not a table"),
  ("factorial(x) where x.has(\"y\")", "cannot apply has on values of type 'integer' and 'string'"),
  ("factorial(xs*) where xs.has(\"y\")", "cannot apply has on values of type 'array' and 'string'"),
  ("factorial(x, ys**) where ys.has(1)", "cannot apply has on values of type 'table' and 'integer'"),
  ("factorial(x, ys**) where ys.has()", "expected 1 argument(s), found 0"),
])
func reportsEvaluationErrors(source: String, message: String) async throws {
  var engine = Engine()
  engine.add(try loadFactorialTrace())
  await #expect {
    try await engine.select(query("select \(source)"))
  } throws: { (e) in
    (e as? Diagnostic)?.message == message
  }
}

@Test func exportsXMLTraceToXML() throws {
  let trace = try loadFactorialTrace()
  let reloaded = try #require(Trace(xml: trace.xml()))
  #expect(reloaded.identity == trace.identity)
  #expect(reloaded.description == trace.description)
}

@Test func exportsUnlabeledSnapsAndColonsInLocationsToXML() throws {
  let source = """
    <pmdb:trace xmlns:pmdb="https://hevs.ch/pmdb" id="2F1B3C8E-6A4D-4E2B-9C1D-0A7E5F3B2C11">
      <pmdb:observations>
        <pmdb:call location="C:\\a:b.py:3">
          <pmdb:function>root</pmdb:function>
          <pmdb:arguments/>
          <pmdb:observations>
            <pmdb:snap location="C:\\a:b.py:4"><pmdb:value><pmdb:function>f</pmdb:function></pmdb:value></pmdb:snap>
          </pmdb:observations>
        </pmdb:call>
      </pmdb:observations>
    </pmdb:trace>
    """
  let trace = try #require(Trace(xml: Data(source.utf8)))
  #expect(trace.calls[0].value.location == SourceLine(3, in: "C:\\a:b.py"))
  #expect(trace.snaps[0].value.label == nil)
  #expect(trace.snaps[0].value.value == .function("f"))

  let reloaded = try #require(Trace(xml: trace.xml()))
  #expect(reloaded.calls[0].value.location == SourceLine(3, in: "C:\\a:b.py"))
  #expect(reloaded.snaps[0].value.location == SourceLine(4, in: "C:\\a:b.py"))
  #expect(reloaded.snaps[0].value.label == nil)
  #expect(reloaded.snaps[0].value.value == .function("f"))
}
