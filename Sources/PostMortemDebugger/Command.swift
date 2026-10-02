import Foundation

/// A command parsed from the REPL.
public enum Command: Hashable, Sendable {

  /// Exits the repl.
  case exit

  /// Loads traces from disk.
  case load(URL, name: String?)

  /// Performs a query selecting observations.
  case select(Query)

  /// Shows the value assigned to the variable in the payload.
  case show(String)

  /// Enumerates convenience variables.
  case showConvenienceVariables

  /// Enumerates the functions whose calls are recorded in the loaded traces.
  case showFunctions

}
