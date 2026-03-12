extension Array {

  /// Creates an instance with enough storage to store `n` elements without allocating new memory.
  public init(minimumCapacity n: Int) {
    self.init()
    self.reserveCapacity(n)
  }

  /// Creates an instance containing `head` followed by the contents of `tail`.
  public init<T: Sequence<Element>>(head: Element, tail: T) {
    self = [head]
    self.append(contentsOf: tail)
  }

}
