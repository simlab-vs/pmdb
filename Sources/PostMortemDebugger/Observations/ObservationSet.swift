/// A collection of observations from one or more traces.
public protocol ObservationSet: Sendable {

  /// A view of the identitis of the traces having observations contained in this set.
  associatedtype Traces: Collection<Trace.ID> where Traces.Index: Sendable

  /// A view of indices of snaps relative to a trace.
  associatedtype Snaps: Collection<Snap.Index>

  /// A view of indices of snaps relative to a trace.
  associatedtype Calls: Collection<Call.Index>

  /// A collection with the identities of the traces having observations contained  in `self`.
  var traces: Traces { get }

  /// Returns the snaps in `self` belonging to `self.traces[i]`.
  func snaps(in i: Traces.Index) -> Snaps

  /// Returns the calls in `self` belonging to `self.traces[i]`.
  func calls(in i: Traces.Index) -> Calls

}
