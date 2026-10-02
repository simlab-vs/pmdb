import Foundation

/// An object responsible for controlling a post-mortem debugging session.
public struct Engine: ~Copyable {

  /// A value bound to a convenience variable in a debugging session.
  public enum ConvenienceValue {

    /// A trace.
    case trace(Trace.ID)

    /// A set of observations.
    case observations(ObservationBuffer)

    /// A textual description of the type of this value.
    public var type: String {
      switch self {
      case .trace: "trace"
      case .observations: "observations"
      }
    }

  }

  /// The traces loaded in memory.
  private var traces: [Trace.ID: Trace]

  /// The source files loaded in memory.
  private var sources: [URL: SourceFile?]

  /// The convenience variables and their assignments.
  private var bindings: [String: ConvenienceValue]

  /// The identifier of the next auto-generated convenience variable.
  private var nextVariableSuffix: Int

  /// Creates an empty instance.
  public init() {
    self.traces = [:]
    self.sources = [:]
    self.bindings = [:]
    self.nextVariableSuffix = 0
  }

  /// The user-defined convenience variables defined in the sessions.
  public var definitions: [(key: String, value: ConvenienceValue)] {
    bindings.sorted(by: \.key)
  }

  /// A set with the observations of all loaded traces.
  public var observations: TraceSet<[Trace.ID: Trace].Values> {
    .init(traces.values)
  }

  /// Assigns `k` to the value `v`.
  public mutating func assign(_ v: ConvenienceValue, for k: String) {
    bindings[k] = v
  }

  /// Returns the value assigned to `k`.
  public func value(for k: String) throws -> ConvenienceValue {
    if let v = bindings[k] { return v }
    let defined = bindings.keys.sorted()
    let known =
      defined.isEmpty ? "no variables are defined" : "defined: " + defined.joined(separator: ", ")
    throw RuntimeError("undefined symbol '\(k)'; \(known)")
  }

  /// The number of recorded calls of each function in the loaded traces, by name.
  public var callCounts: [String: Int] {
    var result: [String: Int] = [:]
    for t in traces.values {
      for c in t.calls where c.index.untagged != 0 {
        result[c.value.function, default: 0] += 1
      }
    }
    return result
  }

  /// Returns a note explaining why the call pattern `q` can't match any recorded call: its function
  /// pattern matches no recorded function (the note names those it partially matches), or no call
  /// of the functions it matches has arguments of the shape of its argument patterns (the note
  /// shows how they were called). Returns `nil` otherwise, or if `q` isn't a call pattern.
  ///
  /// A name partially matches the recorded functions whose names end with `.` and that name (e.g.,
  /// `take` and `Parser.take`); a regular expression, those whose names contain a match.
  public func noteOnUnrecordedFunction(of q: Query) -> String? {
    guard case .call(let f, let xs, _, _, _) = q else { return nil }
    let names = callCounts.keys
    if names.contains(where: f.matches) { return noteOnUnmatchedArguments(f, xs) }

    let partial: [String]
    let note: String
    switch f {
    case .wildcard:
      return nil
    case .exactly(let n):
      partial = names.filter({ (m) in m.hasSuffix("." + n) })
      note = "no call of '\(n)' is recorded"
    case .regex(let r):
      let pattern = try? Regex(String(r.dropFirst().dropLast()))
      partial = names.filter({ (m) in pattern.map({ (p) in m.contains(p) }) ?? false })
      note = "no recorded function's whole name matches \(r)"
    }
    if partial.isEmpty { return note }
    let shown = partial.sorted().prefix(10).joined(separator: ", ")
    return note + "; recorded functions with partial matches: " + shown
      + (partial.count > 10 ? ", …" : "")
  }

  /// Returns a note saying that no recorded call of the functions matching `f` has arguments of
  /// the shape that `xs` matches (the number of positional arguments and the labels of named
  /// ones, whatever their values), describing the shapes of these calls, or `nil` if a call has.
  private func noteOnUnmatchedArguments(_ f: IdentifierPattern, _ xs: ArgumentPatternList) -> String? {
    let shape = ArgumentPatternList(xs.patterns.map({ (p) -> ArgumentPattern in
      switch p {
      case .positional, .positionalLiteral: .positional(binding: nil)
      case .named(let l, _), .namedLiteral(let l, _): .named(label: l, binding: nil)
      case .positionalVariadic: .positionalVariadic(binding: nil)
      case .namedVariadic: .namedVariadic(binding: nil)
      case .universal: .universal
      }
    }))
    var shapes: [String: Int] = [:]
    var count = 0
    for t in traces.values {
      for c in t.calls where c.index.untagged != 0 && f.matches(c.value.function) {
        var e: [String: Value] = [:]
        if shape.matches(argumentsOf: c.value, in: &e) { return nil }
        let named = c.value.named.keys.map({ (k) in k + " = _" })
        let arguments = Array(repeating: "_", count: c.value.positional.count) + named
        shapes["\(c.value.function)(\(arguments.joined(separator: ", ")))", default: 0] += 1
        count += 1
      }
    }
    let shown = shapes.sorted(by: { (a, b) in (a.value, b.key) > (b.value, a.key) }).prefix(3)
      .map({ (k, n) in "\(k) (\(n)×)" }).joined(separator: ", ")
    return "\(count) recorded call(s) of '\(f)', but none has arguments of the shape (\(xs)); "
      + "they were made as " + shown + (shapes.count > 3 ? ", …" : "")
  }

  /// Adds the given trace to the store.
  public mutating func add(_ t: Trace) {
    traces[t.identity] = t
  }

  /// Returns the trace identified by `t`.
  public func trace(_ t: Trace.ID) -> Trace {
    traces[t]!
  }

  /// Returns the contents of the file at `url` or `nil` if it can't be read.
  public mutating func demand(contentsOf url: URL) -> SourceFile? {
    if case .some(let s) = sources[url] {
      return s
    } else {
      let s = SourceFile(contentsOf: url)
      sources[url] = .some(s)
      return s
    }
  }

  /// Returns the result of `query` matched against all observations.
  public func select(_ query: Query) async throws -> ObservationBuffer {
    try await select(query, from: TraceSet(traces.values))
  }

  /// Returns the result of `query` matched against the observations in `haystack`.
  public func select<T: ObservationSet>(
    _ query: Query, from haystack: T
  ) async throws -> ObservationBuffer {
    var accumulator = ObservationBuffer()

    switch query {
    case .all:
      accumulator.formUnion(haystack)

    case .snap(let x, let source, let filter):
      try await reduce(
        select(source, from: haystack), into: &accumulator, { (s, i) in s.snaps(in: i) }
      ) { (buffer, trace, snaps) in
        for o in snaps {
          let s = trace[at: o]
          if let l = s.label, x.matches(l), try satisfied(filter) {
            buffer[trace: trace.identity].snaps.insert(o)
          }
        }
      }

    case .call(let f, let xs, let r, let source, let filter):
      try await reduce(
        select(source, from: haystack), into: &accumulator, { (s, i) in s.calls(in: i) }
      ) { (buffer, trace, calls) in
        var e: [String: Value] = [:]
        for o in calls {
          let s = trace[at: o]
          e.removeAll(keepingCapacity: true)
          if try f.matches(s.function) && xs.matches(argumentsOf: s, in: &e)
            && matches(r, outcomeOf: o, in: trace, binding: &e)
            && satisfied(filter, in: e)
          {
            buffer[trace: trace.identity].calls.insert(o)
          }
        }
      }
    }

    return accumulator
  }

  /// Returns the result of `query` matched against the observations in `haystack`.
  public func select<T: ObservationSet>(
    _ query: Query.FromClause, from haystack: T
  ) async throws -> ObservationBuffer {
    switch query {
    case .variable(let x):
      if case .observations(let s) = try value(for: x) {
        return s
      } else {
        throw RuntimeError("'\(x)' is not an observation set")
      }

    case .query(let q):
      return try await select(q, from: haystack)
    }
  }

  /// Inserts into `accumulator` the results of combining the observations returned by `indices`
  /// using `combine`, for each trace in `source`.
  ///
  /// - Parameters:
  ///   - source: The observations to combine.
  ///   - accumulator: The set into which results are written.
  ///   - indices: A closure that accepts `source` together with the index of a trace `t` in that
  ///     source and returns the indices of the observations belonging to `t` that should be
  ///     combined into `accumulator`.
  ///   - combine: A closure that modifies an accumulator given a trace and a set of observations
  ///     in that trace. Call to `combine` might happen concurrently. The first error thrown by
  ///     `combine` is rethrown.
  private func reduce<T: ObservationSet, U>(
    _ source: T, into accumulator: inout ObservationBuffer,
    _ indices: (T, T.Traces.Index) -> U,
    _ combine: @escaping @Sendable (inout ObservationBuffer, Trace, U) throws -> Void
  ) async throws {
    try await withThrowingTaskGroup(of: ObservationBuffer.self) { (g) in
      for i in source.traces.indices {
        try Task.checkCancellation()
        let t = traces[source.traces[i]]!
        let u = indices(source, i)
        g.addTask {
          var b = ObservationBuffer()
          try combine(&b, t, u)
          return b
        }
      }

      while let xs = try await g.next() {
        accumulator.formUnion(xs)
      }
    }
  }

  /// Returns a fresh convenience variable name.
  public mutating func fresh() -> String {
    defer { nextVariableSuffix += 1 }
    return "$\(nextVariableSuffix)"
  }

}

/// Returns `true` iff `pattern` is `nil` or the outcome of the call `o` in `trace` matches
/// `pattern`, unifying variables in `environment`.
private func matches(
  _ pattern: Query.OutcomePattern?, outcomeOf o: Call.Index, in trace: Trace,
  binding environment: inout [String: Value]
) -> Bool {
  // The payload of an outcome is matched as the only positional argument of a pattern list.
  switch (pattern, trace.outcome(of: o)) {
  case (nil, _):
    return true
  case (.returned(let p), .returned(let v)), (.raised(let p), .raised(let v)):
    return ArgumentPatternList([p]).matches([v], [:], in: &environment)
  default:
    return false
  }
}

/// Returns `true` if either `filter` is `nil` or it evaluates to `true` in `environment`,
/// throwing the error that occurred during the evaluation of `filter`, if any.
///
/// The evaluation of `filter` might not terminate.
private func satisfied(_ filter: Expression?, in environment: [String: Value] = [:]) throws -> Bool {
  guard let f = filter else { return true }
  var e = environment
  return try f.evaluateCondition(in: &e)
}
