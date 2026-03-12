extension Sequence {

  /// Returns `self` sorted according to the ordering of the property of each element at `path`.
  public func sorted<T: Comparable>(by path: KeyPath<Element, T>) -> [Element] {
    self.sorted(by: { (a, b) in a[keyPath: path] < b[keyPath: path] })
  }

}
