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
private func query(_ source: String) throws -> Query {
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
    ├─* call factorial(3)
    │ ├─* call factorial(2)
    │ │ ├─* call factorial(1)
    │ │ └─* snap factorial.$result = 1
    │ └─* snap factorial.$result = 2
    └─* snap factorial.$result = 6

    """
  #expect(trace.description == expected)
}

@Test(arguments: [
  ("factorial(x) where x > 1", 2),
  ("factorial(...)", 3),
  ("_(...)", 4),
  ("/.*\\$result/ where true", 3),
])
func selectsObservations(source: String, count: Int) async throws {
  var engine = Engine()
  engine.add(try loadFactorialTrace())
  let result = try await engine.select(query("select \(source)"))
  #expect(result.count == count)
}
