/// The identity of an observation.
public struct ObservationIdentity: Hashable, Sendable {

  /// The trace to which the observation belongs.
  public let trace: Trace.ID

  /// The index of the observation in its trace.
  public let index: Int

}
