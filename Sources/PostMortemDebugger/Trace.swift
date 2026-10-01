import Archivist
import Foundation

#if canImport(FoundationXML)
  import FoundationXML
#endif

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

extension Trace {

  /// Creates an instance parsing the given XML contents.
  public init?(xml: Data) {
    guard
      let root = try? XMLDocument(data: xml).rootElement(),
      let uuid = root.attribute(forName: "id")?.stringValue.flatMap(UUID.init(uuidString:))
    else { return nil }

    self.identity = UInt128(uuid)
    self.observations = []
    self.snaps = []
    self.calls = []
    self.parent = []
    if !recurse(root, parent: nil) {
      return nil
    }

    func recurse(_ node: XMLElement, parent: Int?) -> Bool {
      // Are there observations?
      guard let children = node
        .elements(forLocalName: "observations", uri: Self.namespace)
        .uniqueElement?.children
      else { return true }

      // Parse observations.
      for n in children where n.uri == Self.namespace {
        let i = observations.count

        // The root has itself for parent and is the only top-level observation.
        if let p = parent {
          self.parent.append(p)
          calls[observations[p].call!].value.append(i)
        } else if i == 0 {
          self.parent.append(i)
        } else {
          return false
        }

        switch n.localName {
        case .some("snap"):
          guard let v = Self.snap(n as! XMLElement) else { return false }
          self.observations.append(.init(snap: snaps.count))
          self.snaps.append(.init(index: .init(untagged: i), value: v))

        case .some("call"):
          guard let v = Self.call(n as! XMLElement) else { return false }
          self.observations.append(.init(call: calls.count))
          self.calls.append(.init(index: .init(untagged: i), value: v))

          // Parse children observations.
          if !recurse(n as! XMLElement, parent: i) { return false }

        default:
          return false
        }
      }

      return true
    }
  }

  /// Returns a snap parsed from the contents of `node`.
  private static func snap(_ node: XMLElement) -> Snap? {
    assert(node.localName == "snap")
    guard
      let l = node.attribute(forName: "location")?.stringValue.flatMap(SourceLine.init(gnu:)),
      let v = node
        .elements(forLocalName: "value", uri: Self.namespace)
        .uniqueElement.flatMap(Self.value(_:))
    else { return nil }
    return Snap(location: l, label: node.attribute(forName: "label")?.stringValue, value: v)
  }

  /// Returns a call parsed from the contents of `node`.
  private static func call(_ node: XMLElement) -> Call? {
    assert(node.localName == "call")
    guard
      let l = node.attribute(forName: "location")?.stringValue.flatMap(SourceLine.init(gnu:)),
      let f = node
        .elements(forLocalName: "function", uri: Self.namespace)
        .uniqueElement?.stringValue,
      let a = node
        .elements(forLocalName: "arguments", uri: Self.namespace)
        .uniqueElement
    else { return nil }

    var positional: [Value] = []
    var named: SortedDictionary<String, Value> = [:]
    for n in (a.children ?? []) where n.uri == Self.namespace {
      guard let v = value(n) else { return nil }
      if let k = (n as! XMLElement).attribute(forName: "label")?.stringValue {
        named[k] = v
      } else {
        positional.append(v)
      }
    }

    return Call(location: l, function: f, positional: positional, named: named)
  }

  /// Returns a value parsed from the contents of `node`.
  private static func value(_ node: XMLNode) -> Value? {
    assert(node.localName == "value")
    guard
      let payload = node.children?.first(where: { (n) in n.kind == .element }),
      payload.uri == Self.namespace
    else { return nil }

    switch payload.localName {
    case .some("none"):
      return .null

    case .some("integer"):
      return payload.stringValue.flatMap(Int64.init(_:)).map(Value.integer(_:))

    case .some("float"):
      return payload.stringValue.flatMap(Double.init(_:)).map(Value.float(_:))

    case .some("string"):
      return payload.stringValue.map(Value.string(_:))

    case .some("function"):
      return payload.stringValue.map(Value.function(_:))

    case .some("array"):
      var elements: [Value] = []
      for n in (payload.children ?? []) where n.kind == .element {
        guard n.uri == Self.namespace, n.localName == "value", let v = value(n) else { return nil }
        elements.append(v)
      }
      return .array(elements)

    case .some("table"):
      var entries: SortedDictionary<String, Value> = [:]
      for n in (payload.children ?? []) where n.kind == .element {
        guard
          n.uri == Self.namespace, n.localName == "value",
          let k = (n as! XMLElement).attribute(forName: "label")?.stringValue,
          entries[k] == nil, let v = value(n)
        else { return nil }
        entries[k] = v
      }
      return .table(entries)

    case .some("object"):
      return payload.stringValue.flatMap { (s) in
        Data.init(base64Encoded: s).flatMap(Array.init(_:)).map(Value.object(_:))
      }

    default:
      return nil
    }
  }

  private static let namespace = "https://hevs.ch/pmdb"

}

extension Trace {

  /// Returns the contents of `self` as an XML document that can be read by `init(xml:)`.
  ///
  /// - Throws: `RuntimeError` if `self` contains a string with characters that can't be written in
  ///   XML 1.0 (e.g., most ASCII control characters).
  public func xml() throws -> Data {
    let root = XMLElement(name: "pmdb:trace")
    root.addNamespace(XMLNode.namespace(withName: "pmdb", stringValue: Self.namespace) as! XMLNode)
    let id = UUID(identity).uuidString
    root.addAttribute(XMLNode.attribute(withName: "id", stringValue: id) as! XMLNode)

    let o = XMLElement(name: "pmdb:observations")
    if !observations.isEmpty {
      try o.addChild(xml(observation: 0))
    }
    root.addChild(o)

    let d = XMLDocument(rootElement: root)
    d.version = "1.0"
    d.characterEncoding = "UTF-8"
    return d.xmlData(options: .nodePrettyPrint)
  }

  /// Returns the XML representation of the observation at index `i` and its children.
  private func xml(observation i: ObservationIndex) throws -> XMLElement {
    if let s = observations[i].snap {
      let snap = snaps[s].value
      let e = try Self.xml(element: "pmdb:snap", location: snap.location)
      if let l = snap.label { try e.addAttribute(Self.xml(attribute: "label", l)) }
      try e.addChild(Self.xml(value: snap.value))
      return e
    }

    let call = calls[observations[i].call!].value
    let e = try Self.xml(element: "pmdb:call", location: call.location)
    try e.addChild(XMLElement(name: "pmdb:function", stringValue: Self.xml(text: call.function)))

    let a = XMLElement(name: "pmdb:arguments")
    for v in call.positional { try a.addChild(Self.xml(value: v)) }
    for (k, v) in call.named { try a.addChild(Self.xml(value: v, label: k)) }
    e.addChild(a)

    if !call.children.isEmpty {
      let o = XMLElement(name: "pmdb:observations")
      for c in call.children { try o.addChild(xml(observation: c)) }
      e.addChild(o)
    }
    return e
  }

  /// Returns an element named `name` with an attribute describing `location`.
  private static func xml(element name: String, location: SourceLine) throws -> XMLElement {
    let e = XMLElement(name: name)
    try e.addAttribute(xml(attribute: "location", location.description))
    return e
  }

  /// Returns a `pmdb:value` element representing `v`, with the given label if any.
  private static func xml(value v: Value, label: String? = nil) throws -> XMLElement {
    let e = XMLElement(name: "pmdb:value")
    if let l = label { try e.addAttribute(xml(attribute: "label", l)) }

    switch v {
    case .null:
      e.addChild(XMLElement(name: "pmdb:none"))
    case .integer(let n):
      e.addChild(XMLElement(name: "pmdb:integer", stringValue: n.description))
    case .float(let n):
      let s = n.isNaN ? "NaN" : n.isInfinite ? (n < 0 ? "-INF" : "INF") : n.description
      e.addChild(XMLElement(name: "pmdb:float", stringValue: s))
    case .string(let s):
      try e.addChild(XMLElement(name: "pmdb:string", stringValue: xml(text: s)))
    case .array(let xs):
      let a = XMLElement(name: "pmdb:array")
      for x in xs { try a.addChild(xml(value: x)) }
      e.addChild(a)
    case .table(let t):
      let a = XMLElement(name: "pmdb:table")
      for (k, x) in t { try a.addChild(xml(value: x, label: k)) }
      e.addChild(a)
    case .function(let f):
      try e.addChild(XMLElement(name: "pmdb:function", stringValue: xml(text: f)))
    case .object(let bytes):
      e.addChild(XMLElement(name: "pmdb:object", stringValue: Data(bytes).base64EncodedString()))
    case .lambda:
      // Lambdas are created by queries, not recorded in traces.
      preconditionFailure("trace contains a lambda")
    }
    return e
  }

  /// Returns an attribute named `name` with value `s`.
  private static func xml(attribute name: String, _ s: String) throws -> XMLNode {
    try XMLNode.attribute(withName: name, stringValue: xml(text: s)) as! XMLNode
  }

  /// Returns `s` iff it can be written in an XML 1.0 document. Otherwise, throws.
  private static func xml(text s: String) throws -> String {
    for c in s.unicodeScalars {
      switch c.value {
      case 0x09, 0x0a, 0x0d, 0x20 ... 0xd7ff, 0xe000 ... 0xfffd, 0x10000 ... 0x10ffff:
        continue
      default:
        throw RuntimeError(
          "cannot write the character U+\(String(c.value, radix: 16, uppercase: true)) in XML")
      }
    }
    return s
  }

}

/// The trace of a program's execution.
public struct Trace: Sendable {

  /// A trace identifier.
  public typealias ID = UInt128

  /// The unique identifier of the trace.
  public let identity: ID

  /// A map from observation identity to its position.
  fileprivate var observations: [ObservationOffset]

  /// A map from a node to its parent.
  fileprivate var parent: [ObservationIndex]

  /// The snapshots recorded in the trace, along with their identities.
  public private(set) var snaps: [ObservationEntry<Snap>]

  /// The calls recorded in the trace, along with their identities.
  public private(set) var calls: [ObservationEntry<Call>]

  /// Creates an instance from the contents of `data`.
  public init<T: Sequence<UInt8>>(archive data: T) throws {
    var archive = ReadableArchive(data)

    // Read the trace's header.
    let header = try archive.read(TraceHeader.self)
    self.identity = header.identifier

    // Parse the trace's contents.
    let count = try Int(archive.readUnsignedLEB128())
    self.observations = .init(minimumCapacity: count)
    self.snaps = .init()
    self.calls = .init()

    for i in 0 ..< count {
      switch try archive.readByte() {
      case 0x01:
        observations.append(.init(snap: snaps.count))
        try snaps.append(.init(index: .init(untagged: i), value: Snap(from: &archive)))

      case 0x02:
        observations.append(.init(call: calls.count))
        try calls.append(.init(index: .init(untagged: i), value: Call(from: &archive)))

      default:
        throw ArchiveError.invalidInput
      }
    }

    self.parent = .init(minimumCapacity: count)
    for i in 0 ..< count {
      let p = try archive.readUnsignedLEB128()

      // The root has itself for parent.
      if (i == 0) && (p == 0) {
        parent.append(0)
        continue
      }

      // Other observations come after their parent, which must be a call.
      guard p < i, let q = observations[Int(p)].call else { throw ArchiveError.invalidInput }
      parent.append(Int(p))
      calls[q].value.append(i)
    }
  }

  /// Creates an instance with the binary or XML archive stored at `url`.
  public init(contentsOf url: URL) throws {
    let data = try Data.init(contentsOf: url)

    if url.pathExtension == "xml" {
      self = try Trace(xml: data) ?? RuntimeError("failed to load a trace from '\(url)'")
    } else {
      self = try Trace(archive: data)
    }
  }

  /// Accesses the observation at index `i`.
  public subscript(at i: ObservationIndex) -> any Observation {
    let offset = observations[i]
    if let s = offset.snap {
      return snaps[s].value
    } else {
      return calls[offset.call!].value
    }
  }

  /// Accesses the observation at index `i`.
  public subscript(at i: Snap.Index) -> Snap {
    snaps[observations[i.untagged].snap!].value
  }

  /// Accesses the observation at index `i`.
  public subscript(at i: Call.Index) -> Call {
    calls[observations[i.untagged].call!].value
  }

  /// Returns the index of the observation following `i` at the same depth, if any.
  fileprivate func sibling(after i: ObservationIndex) -> ObservationIndex? {
    let p = parent[i]

    // Nothing to do if `i` has no parent.
    if p == i { return nil }

    // Is `i` the last child?
    let children = calls[observations[p].call!].value.children
    if let j = children.firstIndex(of: i), j < (children.count - 1) {
      return children[j + 1]
    } else {
      return nil
    }
  }

  /// The index of an observation.
  public typealias ObservationIndex = Int

  /// The tagged index of an observation.
  public struct TaggedObservationIndex<T: Observation>: Hashable, Sendable {

    /// The untagged value of `self`.
    public let untagged: ObservationIndex

  }

  /// An entry in an observation table.
  public struct ObservationEntry<T: Observation>: Sendable {

    /// The index of the observation in the containing trace.
    public let index: T.Index

    /// The value of the observation.
    public fileprivate(set) var value: T

  }

  /// The position of an observation in its corresponding table.
  fileprivate struct ObservationOffset: Hashable {

    /// The raw value of this identity.
    ///
    /// This property denotes an offset in an array which is encoded as follows:
    /// * If `self` identifies a snapshot, then `self.raw` is the encoded offset.
    /// * If `self` identifies a call, then `~self.raw` is the encoded offset.
    private let raw: Int

    /// Creates an instance encoding the position of a snapshot.
    init(snap i: ObservationIndex) { self.raw = i }

    /// Creates an instance encoding the position of a call.
    init(call i: ObservationIndex) { self.raw = ~i }

    /// The payload of `self` iff it encodes the position of a snapshot.
    var snap: ObservationIndex? { raw >= 0 ? raw : nil }

    /// The payload of `self` iff it encodes the position of a call.
    var call: ObservationIndex? { raw < 0 ? ~raw : nil }

  }

}

extension Trace: Hashable {

  public func hash(into hasher: inout Hasher) {
    hasher.combine(identity)
  }

  public static func == (lhs: Self, rhs: Self) -> Bool {
    lhs.identity == rhs.identity
  }

}

extension Trace: Comparable {

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.identity < rhs.identity
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

extension Trace.TaggedObservationIndex: Comparable {

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.untagged < rhs.untagged
  }

}

extension UUID {

  /// Creates an instance with the bytes of `identity`.
  fileprivate init(_ identity: UInt128) {
    var bytes: uuid_t = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    withUnsafeMutableBytes(of: &bytes) { (b) in
      for i in 0 ..< 16 { b[i] = UInt8(truncatingIfNeeded: identity >> ((15 - i) << 3)) }
    }
    self.init(uuid: bytes)
  }

}

extension UInt128 {

  /// Creates an instance copying the bytes of `uuid`.
  fileprivate init(_ uuid: UUID) {
    self = withUnsafePointer(to: uuid.uuid) { (p) in
      p.withMemoryRebound(to: UInt8.self, capacity: 16) { (q) in
        var s = UInt128()
        for i in 0 ..< 16 {
          s |= UInt128(q[i]) << ((15 - i) << 3)
        }
        return s
      }
    }
  }

}
