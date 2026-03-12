/// Returns the application of `action` on a mutable projection of `value`.
public func modify<T, U>(_ value: inout T, _ action: (inout T) throws -> U) rethrows -> U {
  try action(&value)
}
