import Foundation

/// An object responsible for controlling a post-mortem debugging session.
public struct Engine {

  /// The source files loaded in the engine.
  private var sources: [URL: String]

  private var traces: [Trace.ID: Trace]

  /// Creates an empty instance.
  public init() {
    self.sources = [:]
    self.traces = [:]
  }

  /// Loads the given trace.
  public mutating func load(_ t: Trace) {
  }

  /// Returns the observations that satisfy the query `q`.
  public func select(_ q: Query) -> [ObservationIdentity] {
    switch q.entity {
    case .snap:
      return []
    default:
      fatalError()
    }
  }

}
