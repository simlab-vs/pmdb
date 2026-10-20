import Archivist
import BigInt
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
    self.outcomes = findOutcomes()

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

    case .some("boolean"):
      return payload.stringValue.flatMap(Bool.init(_:)).map(Value.boolean(_:))

    case .some("integer"):
      return payload.stringValue.flatMap({ (s) in BigInt(s) }).map(Value.integer(_:))

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
    // The document is written directly rather than with `XMLDocument`, whose serialization doesn't
    // escape whitespace in attribute values on every platform, although XML parsers replace them
    // with spaces.
    var w = XMLWriter()
    w.output.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    let id = UUID(identity).uuidString
    try w.open("pmdb:trace", [("xmlns:pmdb", Self.namespace), ("id", id)])
    w.open("pmdb:observations")
    if !observations.isEmpty {
      try write(observation: 0, to: &w)
    }
    w.close("pmdb:observations")
    w.close("pmdb:trace")
    return Data(w.output.utf8)
  }

  /// Writes the XML representation of the observation at index `i` and its children to `w`.
  private func write(observation i: ObservationIndex, to w: inout XMLWriter) throws {
    if let s = observations[i].snap {
      let snap = snaps[s].value
      var attributes = [("location", snap.location.description)]
      if let l = snap.label { attributes.append(("label", l)) }
      try w.open("pmdb:snap", attributes)
      try Self.write(value: snap.value, to: &w)
      w.close("pmdb:snap")
      return
    }

    let call = calls[observations[i].call!].value
    try w.open("pmdb:call", [("location", call.location.description)])
    try w.leaf("pmdb:function", call.function)

    if call.positional.isEmpty && call.named.isEmpty {
      w.empty("pmdb:arguments")
    } else {
      w.open("pmdb:arguments")
      for v in call.positional { try Self.write(value: v, to: &w) }
      for (k, v) in call.named { try Self.write(value: v, label: k, to: &w) }
      w.close("pmdb:arguments")
    }

    if !call.children.isEmpty {
      w.open("pmdb:observations")
      for c in call.children { try write(observation: c, to: &w) }
      w.close("pmdb:observations")
    }
    w.close("pmdb:call")
  }

  /// Writes a `pmdb:value` element representing `v` to `w`, with the given label if any.
  private static func write(value v: Value, label: String? = nil, to w: inout XMLWriter) throws {
    try w.open("pmdb:value", label.map({ (l) in [("label", l)] }) ?? [])

    switch v {
    case .null:
      w.empty("pmdb:none")
    case .boolean(let b):
      try w.leaf("pmdb:boolean", b.description)
    case .integer(let n):
      try w.leaf("pmdb:integer", n.description)
    case .float(let n):
      let s = n.isNaN ? "NaN" : n.isInfinite ? (n < 0 ? "-INF" : "INF") : n.description
      try w.leaf("pmdb:float", s)
    case .string(let s):
      try w.leaf("pmdb:string", s)
    case .array(let xs):
      w.open("pmdb:array")
      for x in xs { try write(value: x, to: &w) }
      w.close("pmdb:array")
    case .table(let t):
      w.open("pmdb:table")
      for (k, x) in t { try write(value: x, label: k, to: &w) }
      w.close("pmdb:table")
    case .function(let f):
      try w.leaf("pmdb:function", f)
    case .object(let bytes):
      try w.leaf("pmdb:object", Data(bytes).base64EncodedString())
    case .lambda, .builtin:
      // Lambdas are created by queries, not recorded in traces.
      preconditionFailure("trace contains a lambda")
    }

    w.close("pmdb:value")
  }

}

/// A writer of indented XML documents.
private struct XMLWriter {

  /// The text written so far.
  var output = ""

  /// The number of elements that have been opened and not closed.
  private var depth = 0

  /// Writes the start tag of an element named `name` with the given attributes.
  mutating func open(_ name: String, _ attributes: [(String, String)]) throws {
    let a = try Self.attributes(attributes)
    indent()
    output.write("<\(name)\(a)>\n")
    depth += 1
  }

  /// Writes the start tag of an element named `name` without attributes.
  mutating func open(_ name: String) {
    indent()
    output.write("<\(name)>\n")
    depth += 1
  }

  /// Writes the end tag of an element named `name`.
  mutating func close(_ name: String) {
    depth -= 1
    indent()
    output.write("</\(name)>\n")
  }

  /// Writes an empty element named `name`.
  mutating func empty(_ name: String) {
    indent()
    output.write("<\(name)/>\n")
  }

  /// Writes an element named `name` containing the text `s`.
  mutating func leaf(_ name: String, _ s: String) throws {
    let t = try Self.escaped(s, inAttribute: false)
    indent()
    output.write("<\(name)>\(t)</\(name)>\n")
  }

  /// Writes the indentation of the current line.
  private mutating func indent() {
    output.write(String(repeating: "  ", count: depth))
  }

  /// Returns the given attributes as they are written in a start tag.
  private static func attributes(_ attributes: [(String, String)]) throws -> String {
    try attributes.map({ (n, v) in " \(n)=\"\(try escaped(v, inAttribute: true))\"" }).joined()
  }

  /// Returns `s` with the characters that have a special meaning in XML replaced by references.
  ///
  /// Carriage returns are always replaced because XML parsers normalize line endings, and tabs
  /// and line feeds are replaced in attribute values because XML parsers replace them with spaces.
  ///
  /// - Throws: `RuntimeError` if `s` contains characters that can't be written in XML 1.0.
  private static func escaped(_ s: String, inAttribute: Bool) throws -> String {
    var result = ""
    for c in s.unicodeScalars {
      switch c.value {
      case 0x26: result.write("&amp;")
      case 0x3c: result.write("&lt;")
      case 0x3e: result.write("&gt;")
      case 0x22 where inAttribute: result.write("&quot;")
      case 0x09 where inAttribute: result.write("&#9;")
      case 0x0a where inAttribute: result.write("&#10;")
      case 0x0d: result.write("&#13;")
      case 0x09, 0x0a, 0x20 ... 0xd7ff, 0xe000 ... 0xfffd, 0x10000 ... 0x10ffff:
        result.unicodeScalars.append(c)
      default:
        throw RuntimeError(
          "cannot write the character U+\(String(c.value, radix: 16, uppercase: true)) in XML")
      }
    }
    return result
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

  /// A map from the offset of each call in `calls` to the index of the snap recording the value it
  /// returned or the exception it raised, if any.
  fileprivate var outcomes: [ObservationIndex?] = []

  /// Creates an instance from the contents of `data`.
  public init<T: Sequence<UInt8>>(archive data: T) throws {
    var archive = ReadableArchive(data)

    // Read the trace's header.
    let header = try archive.read(TraceHeader.self)
    self.identity = header.identifier

    // Read the table of values, from version 1.1 on, whose values refer to earlier ones.
    let table = ValueTable()
    var context: Any = table
    if (header.major, header.minor) >= (1, 1) {
      let n = try Int(archive.readUnsignedLEB128())
      table.values.reserveCapacity(n)
      for _ in 0 ..< n { try table.values.append(archive.read(Value.self, in: &context)) }
    }

    // Parse the trace's contents.
    let count = try Int(archive.readUnsignedLEB128())
    self.observations = .init(minimumCapacity: count)
    self.snaps = .init()
    self.calls = .init()

    var explicitOutcomes: [(call: Int, snap: ObservationIndex)] = []
    for i in 0 ..< count {
      let tag = try archive.readByte()
      switch tag {
      case 0x01:
        observations.append(.init(snap: snaps.count))
        try snaps.append(.init(index: .init(untagged: i), value: Snap(from: &archive, in: &context)))

      case 0x02, 0x04:
        observations.append(.init(call: calls.count))
        try calls.append(
          .init(index: .init(untagged: i), value: Call(from: &archive, withParameters: tag == 0x04, in: &context)))

      case 0x03:
        // The outcome of the call at an earlier index, read as a snap labeled `<function>.$result`
        // or `<function>.$exception`.
        let location = try archive.read(SourceLine.self)
        let c = try Int(archive.readUnsignedLEB128())
        let raised = try archive.readByte() != 0
        let value = try archive.read(Value.self, in: &context)
        guard c < i, let q = observations[c].call else { throw ArchiveError.invalidInput }
        let label = calls[q].value.function + (raised ? ".$exception" : ".$result")
        explicitOutcomes.append((q, i))
        observations.append(.init(snap: snaps.count))
        snaps.append(
          .init(index: .init(untagged: i), value: Snap(location: location, label: label, value: value)))

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
    self.outcomes = findOutcomes()
    for (c, j) in explicitOutcomes { outcomes[c] = j }
  }

  /// Returns the index of the snap recording the outcome of each call, by offset in `calls`.
  ///
  /// The outcome of a call is the snap labeled `<function>.$result` or `<function>.$exception`
  /// immediately following that call in the children of its parent.
  fileprivate func findOutcomes() -> [ObservationIndex?] {
    var result = [ObservationIndex?](repeating: nil, count: calls.count)
    for c in calls {
      let children = c.value.children
      for (a, b) in zip(children, children.dropFirst()) {
        guard
          let i = observations[a].call, let j = observations[b].snap,
          let l = snaps[j].value.label
        else { continue }
        let f = calls[i].value.function
        if (l == f + ".$result") || (l == f + ".$exception") { result[i] = b }
      }
    }
    return result
  }

  /// The way in which a call ended.
  public enum Outcome: Sendable {

    /// The call returned the payload.
    case returned(Value)

    /// The call raised the payload.
    case raised(Value)

  }

  /// Returns the value returned or the exception raised by the call at index `i`, if recorded.
  public func outcome(of i: Call.Index) -> Outcome? {
    guard let j = outcomes[observations[i.untagged].call!] else { return nil }
    let s = snaps[observations[j].snap!].value
    return s.label!.hasSuffix(".$result") ? .returned(s.value) : .raised(s.value)
  }

  /// Returns a description of the call at index `i` together with its outcome, if recorded.
  public func description(of i: Call.Index) -> String {
    Self.describe(self[at: i], outcome: outcome(of: i))
  }

  /// Returns a description of `call` and its outcome.
  private static func describe(_ call: Call, outcome: Outcome?) -> String {
    switch outcome {
    case .returned(let v):
      return "\(call) -> \(v)"
    case .raised(let v):
      return "\(call) raised \(v)"
    case nil:
      return "\(call)"
    }
  }

  /// Creates an instance with the binary or XML archive stored at `url`.
  public init(contentsOf url: URL) throws {
    let data: Data
    do {
      data = try Data(contentsOf: url)
    } catch let e {
      let reason =
        FileManager.default.fileExists(atPath: url.path) ? e.localizedDescription : "no such file"
      throw RuntimeError("cannot read '\(url.relativePath)': \(reason)")
    }

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
      // The outcomes of calls are written on the same line as the calls rather than as snaps.
      let hidden = Set(outcomes.compactMap(\.self))
      var result = ""
      write(observation: observations[0], to: &result, prefix: nil, hiding: hidden)
      return result
    }
  }

  /// Writes a textual representation of the observation at position `i` and its children to
  /// `output`.
  ///
  /// - Parameters:
  ///   - prefix: The text written before the observation and the connector linking it to its
  ///     parent, which is `nil` for the root.
  ///   - hidden: The indices of the observations that should not be written.
  private func write(
    observation i: ObservationOffset, to output: inout String,
    prefix: (text: String, isLast: Bool)?, hiding hidden: Set<ObservationIndex>
  ) {
    if let p = prefix {
      output.write(p.text)
      output.write(p.isLast ? "└─" : "├─")
    }
    output.write("* ")

    if let j = i.snap {
      output.write(String(describing: snaps[j].value))
      output.write("\n")
      return
    }

    let call = calls[i.call!]
    output.write(description(of: call.index))
    output.write("\n")

    let indentation = prefix.map({ (p) in p.text + (p.isLast ? "  " : "│ ") }) ?? ""
    let shown = call.value.children.filter({ (c) in !hidden.contains(c) })
    for (k, c) in shown.enumerated() {
      write(
        observation: observations[c], to: &output,
        prefix: (indentation, k == shown.count - 1), hiding: hidden)
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
