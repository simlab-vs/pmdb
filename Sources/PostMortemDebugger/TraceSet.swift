/// A set of traces.
public struct TraceSet<T: Collection<Trace> & Sendable> {

  /// The traces in the set.
  public let members: T

  /// Creates an instance with the given traces.
  public init(_ members: T) {
    self.members = members
  }

}

extension TraceSet: ObservationSet {

  public typealias Traces = LazyMapSequence<T, Trace.ID>

  public var traces: Traces {
    members.lazy.map(\.identity)
  }

  public func snaps(in i: T.Index) -> some Collection<Snap.Index> {
    members[i].snaps.lazy.map(\.index)
  }

  public func calls(in i: T.Index) -> some Collection<Call.Index> {
    members[i].calls.lazy.map(\.index)
  }

}
