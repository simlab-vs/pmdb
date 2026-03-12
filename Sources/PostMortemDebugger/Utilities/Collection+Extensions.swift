extension Collection {

  /// Returns contents of `self` iff self contains exactly one element.
  public var uniqueElement: Element? {
    let s = startIndex
    return (index(after: s) == endIndex) ? self[s] : nil
  }

}
