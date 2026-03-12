/// The expression of a query selecting observations.
public enum Query: Hashable, Sendable {

  /// All observations.
  case all

  /// Calls that match the given pattern.
  ///
  /// An observation is matched iff it is a call in which the name of the function being applied
  /// matches `callee` and the arguments of the call match `arguments`.
  case call(IdentifierPattern, ArgumentPatternList, from: FromClause, where: Expression?)

  /// Snaps that match the given pattern.
  ///
  /// An observation is matched iff it is a snap in which the label matches the given pattern.
  case snap(IdentifierPattern, from: FromClause, where: Expression?)

  /// The expression of the source in which the results of a query are picked.
  public indirect enum FromClause: Hashable, Sendable {

    /// A convenience variable.
    case variable(String)

    /// The result of another query.
    case query(Query)

  }

}
