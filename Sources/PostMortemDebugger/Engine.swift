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
    try bindings[k] ?? RuntimeError("undefined symbol '\(k)'")
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
      // The result of a call is matched as the only positional argument of a pattern list.
      let results = r.map({ (p) in ArgumentPatternList([p]) })
      try await reduce(
        select(source, from: haystack), into: &accumulator, { (s, i) in s.calls(in: i) }
      ) { (buffer, trace, calls) in
        var e: [String: Value] = [:]
        for o in calls {
          let s = trace[at: o]
          e.removeAll(keepingCapacity: true)
          if try f.matches(s.function) && xs.matches(argumentsOf: s, in: &e)
            && matches(results, resultOf: o, in: trace, binding: &e)
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

/// Returns `true` iff `pattern` is `nil` or the call `o` in `trace` returned a value matching
/// `pattern`, unifying variables in `environment`.
private func matches(
  _ pattern: ArgumentPatternList?, resultOf o: Call.Index, in trace: Trace,
  binding environment: inout [String: Value]
) -> Bool {
  guard let p = pattern else { return true }
  if case .returned(let v) = trace.outcome(of: o) {
    return p.matches([v], [:], in: &environment)
  } else {
    return false
  }
}

/// Returns `true` if either `filter` is `nil` or it evaluates to a truthy value in `environment`,
/// throwing the error that occurred during the evaluation of `filter`, if any.
///
/// The evaluation of `filter` might not terminate.
private func satisfied(_ filter: Expression?, in environment: [String: Value] = [:]) throws -> Bool {
  guard let f = filter else { return true }
  var e = environment
  return try f.evaluate(in: &e).isTruthy
}
