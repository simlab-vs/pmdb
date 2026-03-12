/// A dynamically sized collection of observations from one or more traces.
public struct ObservationBuffer: Sendable {

  /// The indices of observations in a buffer relative to a particular trace.
  public struct Slot: Sendable {

    /// The indices of the snaps.
    public var snaps: SortedSet<Snap.Index>

    /// The indices of the calls.
    public var calls: SortedSet<Call.Index>

    /// Creates an empty instance.
    public init() {
      self.snaps = []
      self.calls = []
    }

    /// `true` if this `self` contains no observation.
    public var isEmpty: Bool {
      snaps.isEmpty && calls.isEmpty
    }

  }

  /// The identities of observations in the buffer, indexed by the trace in which they belong.
  private var contents: SortedDictionary<Trace.ID, Slot>

  /// Creates an empty instance.
  public init() {
    self.contents = [:]
  }

  /// The number of elements in the collection.
  public var count: Int {
    contents.values.reduce(0) { (s, os) in s + os.snaps.count + os.calls.count }
  }

  /// Accesses the observations in `self` that belong to `t`.
  public subscript(trace t: Trace.ID) -> Slot {
    get { contents[t] ?? .init() }
    _modify {
      if let i = contents.index(forKey: t) {
        defer { if contents[value: i].isEmpty { contents.remove(at: i) } }
        yield &contents[value: i]
      } else {
        var s = Slot()
        defer { if !s.isEmpty { contents[t] = s } }
        yield &s
      }
    }
  }

  /// Inserts all observations contained in `other` into `self`.
  public mutating func formUnion<T: ObservationSet>(_ other: T) {
    for i in other.traces.indices {
      let t = other.traces[i]
      modify(&contents[t, default: .init()]) { (slot) in
        slot.snaps.formUnion(.init(other.snaps(in: i)))
        slot.calls.formUnion(.init(other.calls(in: i)))
      }
    }
  }

}

extension ObservationBuffer: ObservationSet {

  public typealias Traces = SortedSet<Trace.ID>

  public var traces: Traces {
    contents.keys
  }

  public func snaps(in i: Int) -> SortedSet<Snap.Index> {
    contents.values[i].snaps
  }

  public func calls(in i: Int) -> SortedSet<Call.Index> {
    contents.values[i].calls
  }

}
