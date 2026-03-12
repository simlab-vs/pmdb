/// A record of an event that occurred during the execution of a program.
public protocol Observation: Sendable {

  /// The source location to which this observation is attached.
  var location: SourceLine { get }

}


extension Observation {

  /// The index of an instance of `Self` relative to the trace to which it belongs.
  public typealias Index = Trace.TaggedObservationIndex<Self>

}
