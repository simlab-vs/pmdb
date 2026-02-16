public struct Query: Hashable, Sendable {

  public enum Entity: Hashable, Sendable {

    case snap

    case call

    case all

  }

  public let entity: Entity

  public let filter: QueryFilter?

}

public enum QueryFilter: Hashable, Sendable {

  case under(callee: String, depth: Int?)

}
