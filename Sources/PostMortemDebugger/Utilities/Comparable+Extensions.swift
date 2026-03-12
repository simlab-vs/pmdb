extension Comparable {

  /// Returns the value closest to `self` that is within `range`.
  public func within(_ range: ClosedRange<Self>) -> Self {
    if self < range.lowerBound {
      range.lowerBound
    } else if self > range.upperBound {
      range.upperBound
    } else {
      self
    }
  }

}
