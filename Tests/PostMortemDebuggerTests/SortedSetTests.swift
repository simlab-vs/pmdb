import Testing
@testable import PostMortemDebugger

/// All subsets of `0 ..< 5`.
private let subsets: [SortedSet<Int>] = (0 ..< 32).map { (m) in
  SortedSet((0 ..< 5).filter({ (i) in m & (1 << i) != 0 }))
}

@Test func setAlgebraMatchesStandardSet() {
  for a in subsets {
    for b in subsets {
      let (x, y) = (Set(a), Set(b))
      #expect(Array(a.union(b)) == x.union(y).sorted(), "\(a) ∪ \(b)")
      #expect(Array(a.intersection(b)) == x.intersection(y).sorted(), "\(a) ∩ \(b)")
      #expect(Array(a.symmetricDifference(b)) == x.symmetricDifference(y).sorted(), "\(a) ∆ \(b)")
      #expect(Array(a.subtracting(b)) == x.subtracting(y).sorted(), "\(a) \\ \(b)")
    }
  }
}

@Test func updateWith() {
  var s: SortedSet<Keyed> = [.init(key: 1, payload: "a"), .init(key: 3, payload: "c")]

  // Updating with an absent member inserts it and returns `nil`.
  #expect(s.update(with: .init(key: 2, payload: "b")) == nil)
  #expect(s.map(\.payload) == ["a", "b", "c"])

  // Updating with a present member replaces it and returns the member it replaced.
  #expect(s.update(with: .init(key: 1, payload: "z"))?.payload == "a")
  #expect(s.map(\.payload) == ["z", "b", "c"])
}

/// An element whose equality and ordering are defined by `key` alone, ignoring `payload`.
private struct Keyed: Comparable {

  /// The value defining the identity of `self`.
  let key: Int

  /// A value that takes no part in equality or ordering.
  let payload: String

  static func < (l: Self, r: Self) -> Bool {
    l.key < r.key
  }

  static func == (l: Self, r: Self) -> Bool {
    l.key == r.key
  }

}
