import Archivist

/// Metadata about a trace archive.
public struct TraceHeader: Sendable {

  /// The major version number of the archive.
  public let major: UInt8

  /// The minor version number of the archive.
  public let minor: UInt8

  /// The unique identifier of the trace.
  public let identifier: Trace.ID

  /// The magic header that is written at the beginning of a trace archive.
  public static let MAGIC_NUMBER: UInt32 = 0x706d6462

}

extension TraceHeader: Archivable {

  public init<T>(from archive: inout ReadableArchive<T>, in _: inout Any) throws {
    // Parse the magic number.
    let magic = try archive.read(UInt32.self, endianness: .big)
    if magic != Self.MAGIC_NUMBER {
      throw ArchiveError.invalidInput
    }

    // Parse the version.
    self.major = try archive.readByte()
    self.minor = try archive.readByte()

    // Parse the identifier, which is encoded as 16 bytes.
    var u: UInt128 = 0
    for i in 0 ..< 16 {
      if i > 0 { u = u << 8 }
      u = try u | UInt128(archive.readByte())
    }
    self.identifier = u
  }

  public func write<T>(to archive: inout WriteableArchive<T>, in _: inout Any) throws {
    archive.write(Self.MAGIC_NUMBER, endianness: .big)
    archive.write(byte: major)
    archive.write(byte: minor)
  }

}

/// The trace of a program's execution.
public struct Trace: Sendable {

  /// A trace identifier.
  public typealias ID = UInt128

  /// The unique identifier of the trace.
  public let identifier: ID

  /// A map from observation identity to its position.
  private var observations: [ObservationOffset]

  /// The snapshots recorded in the trace, along with their identities.
  private var snaps: [ObservationEntry<Snap>]

  /// The calls recorded in the trace, along with their identities.
  private var calls: [ObservationEntry<Call>]

  /// A map from a node to its parent.
  private var parent: [Int]

  /// Creates an instance from the contents of `data`.
  public init<T: Sequence<UInt8>>(archive data: T) throws {
    var archive = ReadableArchive(data)

    // Read the trace's header.
    let header = try archive.read(TraceHeader.self)
    self.identifier = header.identifier

    // Parse the trace's contents.
    let count = try Int(archive.readUnsignedLEB128())
    self.observations = .init(minimumCapacity: count)
    self.snaps = .init()
    self.calls = .init()
    self.parent = .init(minimumCapacity: count)

    for i in 0 ..< count {
      switch try archive.readByte() {
      case 0x01:
        observations.append(.init(snap: snaps.count))
        try snaps.append(.init(id: i, value: Snap(from: &archive)))

      case 0x02:
        observations.append(.init(call: calls.count))
        try calls.append(.init(id: i, value: Call(from: &archive)))

      default:
        throw ArchiveError.invalidInput
      }
    }

    for i in 0 ..< count {
      let p = try Int(archive.readUnsignedLEB128())

      // The root has itself for parent.
      if p == i { continue }

      // The observation must be a call.
      if let q = observations[p].call {
        calls[q].value.append(i)
      } else {
        throw ArchiveError.invalidInput
      }
    }
  }

  /// Returns the observations that satisfy the query `q`.
  public func select(_ q: Query) -> [ObservationIdentity] {
    switch q.entity {
    case .snap:
      return selectSnaps(where: q.filter)
    default:
      fatalError()
    }
  }

  public func selectSnaps(where filter: QueryFilter? = nil) -> [ObservationIdentity] {
    guard let f = filter else {
      return snaps.map({ e in .init(trace: identifier, index: e.id) })
    }

    var result: [ObservationIdentity] = []
    for e in snaps where satisfies(e, f) {
      result.append(.init(trace: identifier, index: e.id))
    }
    return result
  }

  private func satisfies<T: Observation>(_ o: ObservationEntry<T>, _ f: QueryFilter) -> Bool {
    switch f {
    case .under(let callee, let depth):
      let m = depth ?? Int.max
      var d = 0
      var j = o.id
      while (parent[j] != j) && (d < m) {
        j = parent[j]
        d += 1

        // Is the filter defined for a specific depth?
        if (depth == nil) || (d != m) { continue }

        // Did we get to a parent we're looking for.
        if let p = observations[j].call {
          if calls[p].value.function == callee { return true }
        }
      }

      return false
    }
  }

  /// An entry in an observation table.
  private struct ObservationEntry<T: Observation>: Sendable {

    /// The identity of the observation.
    let id: Int

    /// The value of the observation.
    var value: T

  }

  /// The position of an observation in its corresponding table.
  private struct ObservationOffset: Hashable {

    /// The raw value of this identity.
    ///
    /// This property denotes an offset in an array which is encoded as follows:
    /// * If `self` identifies a snapshot, then `self.raw` is the encoded offset.
    /// * If `self` identifies a call, then `~self.raw` is the encoded offset.
    private let raw: Int

    /// Creates an instance encoding the position of a snapshot.
    init(snap i: Int) { self.raw = i }

    /// Creates an instance encoding the position of a call.
    init(call i: Int) { self.raw = ~i }

    /// The payload of `self` iff it encodes the position of a snapshot.
    var snap: Int? { raw >= 0 ? raw : nil }

    /// The payload of `self` iff it encodes the position of a call.
    var call: Int? { raw < 0 ? ~raw : nil }

  }

}

extension Trace: CustomStringConvertible {

  public var description: String {
    if observations.isEmpty {
      return ""
    } else {
      var result = ""
      write(observation: observations[0], to: &result, depth: 0, isLast: observations.count == 1)
      return result
    }
  }

  /// Writes a textual representation of the observation at position `i` to `output`.
  ///
  /// - Parameters:
  ///   - depth: The depth of the observation in the call tree encoded by the trace.
  ///   - isLast: `true` iff `i` is the last child of its parent.
  private func write(
    observation i: ObservationOffset, to output: inout String, depth: Int, isLast: Bool
  ) {
    if depth > 1 {
      output.write(String(repeating: "│ ", count: depth - 1))
    }
    if depth > 0 {
      output.write(isLast ? "└─" : "├─")
    }

    output.write("* ")

    if let j = i.snap {
      write(snap: j, to: &output, depth: depth)
    } else {
      write(call: i.call!, to: &output, depth: depth)
    }
  }

  /// Implements `write(observation:to:depth:isLast)` for snapshots.
  private func write(snap i: Int, to output: inout String, depth: Int) {
    output.write(String(describing: snaps[i].value))
    output.write("\n")
  }

  /// Implements `write(observation:to:depth:isLast)` for calls.
  private func write(call i: Int, to output: inout String, depth: Int) {
    let call = calls[i]

    output.write(String(describing: call.value))
    output.write("\n")

    for c in call.value.children.dropLast() {
      write(observation: observations[c], to: &output, depth: depth + 1, isLast: false)
    }
    if let c = call.value.children.last {
      write(observation: observations[c], to: &output, depth: depth + 1, isLast: true)
    }
  }

}
