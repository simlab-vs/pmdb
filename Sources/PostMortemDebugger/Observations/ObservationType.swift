/// A tag identifying the type of an observation.
public enum ObservationType: UInt8, Hashable, Sendable {

  /// A snap.
  case snap = 0x01

  /// A call.
  case call = 0x02

}
