import Foundation

extension Value {

  /// The JSON representation of `self`, as written by `export`.
  ///
  /// `none` is `null`; Booleans, integers of any size, and finite floating-point numbers are JSON
  /// literals; strings are strings; arrays are arrays; tables are objects. Values that JSON can't
  /// represent are objects with a single key starting with `$`: `{"$float": "NaN"}` (or
  /// `"Infinity"`, `"-Infinity"`), `{"$function": "<name>"}` and `{"$object": null}` for objects
  /// the recorder couldn't describe.
  public var json: String {
    switch self {
    case .null:
      return "null"
    case .boolean(let b):
      return b ? "true" : "false"
    case .integer(let n):
      return n.description
    case .float(let x):
      if x.isNaN { return #"{"$float": "NaN"}"# }
      if x.isInfinite { return x < 0 ? #"{"$float": "-Infinity"}"# : #"{"$float": "Infinity"}"# }
      return x.description
    case .string(let s):
      return Self.json(string: s)
    case .array(let xs):
      return "[" + xs.map(\.json).joined(separator: ", ") + "]"
    case .table(let t):
      return "{" + t.map({ (k, v) in Self.json(string: k) + ": " + v.json }).joined(separator: ", ")
        + "}"
    case .function(let f):
      return #"{"$function": "# + Self.json(string: f) + "}"
    case .object:
      return #"{"$object": null}"#
    case .lambda, .builtin:
      // Lambdas and builtins are created by queries, not recorded in traces.
      preconditionFailure("not a recorded value")
    }
  }

  /// Returns `s` as a JSON string literal.
  public static func json(string s: String) -> String {
    var result = "\""
    for c in s.unicodeScalars {
      switch c {
      case "\"": result += "\\\""
      case "\\": result += "\\\\"
      case "\n": result += "\\n"
      case "\r": result += "\\r"
      case "\t": result += "\\t"
      case _ where c.value < 0x20:
        result += String(format: "\\u%04x", c.value)
      default:
        result.unicodeScalars.append(c)
      }
    }
    return result + "\""
  }

}

extension Trace {

  /// Returns the JSON object describing the call at index `i` and its outcome, as written by
  /// `export`: its `location`, `function`, `positional` and `named` arguments, and the value it
  /// `returned` or the exception it `raised`, if recorded.
  public func json(call i: Call.Index) -> String {
    let c = self[at: i]
    var fields = [
      ("location", Value.json(string: c.location.description)),
      ("function", Value.json(string: c.function)),
      ("positional", Value.array(c.positional).json),
      ("named", Value.table(c.named).json),
    ]
    switch outcome(of: i) {
    case .returned(let v): fields.append(("returned", v.json))
    case .raised(let v): fields.append(("raised", v.json))
    case nil: break
    }
    return "{" + fields.map({ (k, v) in "\"\(k)\": \(v)" }).joined(separator: ", ") + "}"
  }

  /// Returns the JSON object describing `snap`, as written by `export`: its `location`, `label` and
  /// `value`.
  public static func json(snap s: Snap) -> String {
    let label = s.label.map(Value.json(string:)) ?? "null"
    return #"{"location": "# + Value.json(string: s.location.description)
      + #", "label": "# + label + #", "value": "# + s.value.json + "}"
  }

}
