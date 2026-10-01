# pmdb

`pmdb` is a language-agnostic "post-mortem" debugger.
It provides users with a holistic view of a program's behavior and lets them identify interesting events using queries rather than careful step-by-step forward execution.

Unlike a traditional live debugger, a post-mortem debugger operates on the traces of a program's execution, after that program has finished running.
This approach is related but different from [time-travel debugging](https://en.wikipedia.org/wiki/Time_travel_debugging), which extends traditional debugging with the ability to go back to a previous state.

## Description

In the context of this project, a trace is not a sequence of statements having been visited but rather a collection of *observations* about the program's execution.
These observations are structured into a tree whose nodes correspond to call frames.
That is, each child of a node is an observation that happened within the frame of the corresponding function.

`pmdb` is language-agnostic but it requires a way to instrument the program under study to generate a trace of its execution(s).
A prototype library for instrumenting Python programs is currently available.

To illustrate, consider the following Python program:

```python
import recorder as pmdb

@pmdb.main.record
def factorial(n):
  return 1 if n < 2 else n * factorial(n - 1)

if __name__ == "__main__":
  n = pmdb.main.run(factorial, 3)
  print(n)  # Prints 6

  with open("factorial.trace", "wb") as f:
    archive = pmdb.main.serialize()
    f.write(archive.buffer)
```

The decorator on `factorial` indicates that calls to this function should be traced.
Every call to a decorated function is recorded, so evaluating `factorial(3)` (here by means of `pmdb.main.run`, which simply applies a function to the given arguments) records 3 calls in a trace that is then serialized and saved on disk.

Each recorded call is followed by a snap labeled `<function>.$result` holding the value returned by the call.
If the call raises instead, the snap is labeled `<function>.$exception` and holds a table with the `type` of the exception and its `message`.
Arguments, results, and snaps are recorded in the state they have when they are observed.
`None` is recorded as `none`, lists and tuples as arrays, and dictionaries with string keys and named tuples as tables.
Members of enumerations are recorded as their names.
A class can choose how its instances are recorded by defining a method `__pmdb__` returning the value to record instead, and `pmdb.register(cls, convert)` does the same for classes one cannot modify.
Other objects are pickled, or recorded as the string returned by `repr` if they cannot be pickled.

The serialized trace contains the following tree:

```
pmdb --show factorial.trace
* call root()
├─* call factorial(3)
│ ├─* call factorial(2)
│ │ ├─* call factorial(1)
│ │ └─* snap factorial.$result = 1
│ └─* snap factorial.$result = 2
└─* snap factorial.$result = 6
```

A recorder for Rust programs is also available in [Rust](Rust).
It records the same program as follows:

```rust
use pmdb_recorder as pmdb;

#[pmdb::record]
fn factorial(n: u64) -> u64 {
  if n < 2 { 1 } else { n * factorial(n - 1) }
}

fn main() -> std::io::Result<()> {
  let n = factorial(3);
  println!("{n}"); // Prints 6
  pmdb::main().write_to("factorial.trace")
}
```

Values are recorded according to their implementation of the trait `pmdb::Record`, which can be derived.
Structs with named fields are recorded as tables, enums whose variants have no fields as the names of their variants, and other enums as tables mapping `$variant` to the name of their variant and each field to its value.
Values of types that do not implement `Record` are recorded as a string naming their type.
See the documentation of the crate `pmdb-recorder` for details.

Once a trace has been recorded, `pmdb` can be used to explore that trace interactively, by means of a domain specific language.
The following session illustrates:

```
pmdb factorial.trace
(pmdb) select factorial(x) where x > 1
$0 = <2 element(s) in 1 trace(s)>
(pmdb) show $0
factorial.py:8: call factorial(3)
     6 |
     7 | if __name__ == "__main__":
>    8 |   n = pmdb.main.run(factorial, 3)
     9 |   print(n)  # Prints 6
    10 |
continue? [Y/n] n
(pmdb) exit
```

A trace can be converted to the human-readable XML format described in [Documentation/Traces.md](Documentation/Traces.md) with `pmdb --export-xml factorial.trace > factorial.xml`.
`pmdb` loads traces whose names end with `.xml` as XML documents.

Commands can also be passed on the command line with `-e` (or `--execute`), in which case `pmdb` runs them in order and exits instead of starting a session.
Each query lists the observations it selects, `show` prints all observations without asking to continue, and the results of queries are numbered `$0`, `$1`, etc. so that later commands can refer to them.
`pmdb` stops at the first command that fails, exiting with a non-zero status.

```
pmdb factorial.trace -e 'select factorial(x) where x > 1' -e 'select _(...) from $0' -e 'show $1'
```

A more detailed description of the `pmdb`'s query language is given below.

It is possible to load more than one single trace during a debugging session, to explore multiple traces at once.
Queries will return observations from all queries at once.

## Getting started

`pmdb` is written in Swift and can be built from sources using its default package manager.
Install Swift on your system [as per instructions](https://www.swift.org/install/macos/), clone this repository, and finally build `pmdb` with the following command:

```
swift build -c release
```

A standalone executable will be written to the folder `.build/release`.

## Query Language

> Note that the query language is still under developement and that its syntax and features may change.

`pmdb` comes with a query language that can be used to find observations of interest in a trace.
A query has the following form:

```
<pattern> [from <source>] [where <expression>]
```

Two kinds of patterns exist: snap patterns and call patterns.
The former can match snap observations (i.e., observations of a specific value at one point of the program) and the latter can match call observations (i.e., observations of function calls).
More details are given below.

The from clause, if provided, defines the source of the query which, specifies the set of observations in which the query will be executed.
In the absence of a from clause, a query selects from all available observations in all traces.

The where clause, if provided, defines a filter that is applied on all results matching the pattern.
This filter is given as an expression denoting a pedicate satisfied if and only if the expression evaluates to a truthy value.
More details are given below.

### Snap Patterns

A snap pattern is defined as an identifier pattern, matching the label of the observed value.
This pattern can be a simple identifier, a regular expression, of a wildcard.
Regular expressions are enclosed in a pair of forward slashes.
For example, the pattern `/.*\$result/` matches any snap whose label is suffixed by `$result`.
Wildcards are written with a single underscore (i.e., `_`).

### Call Patterns

A call pattern has the following form:

```
<identifier-pattern>(<argument-pattern> ...)
```

The first pattern serves to match the name of the function being called whereas the argument patterns serve to match argument values.
Argument patterns are separated by a comma and can be positional or named, to match positional or named arguments, respectively.

A positional pattern can be either a wildcard (i.e., `_`) or a variable.
Repeated occurrences ofthe same variable can be used to represent the same value during pattern matching.
For example, the pattern `f(x, x)` matches any call to a function `f` with the same value twice (e.g., `f(1, 1)` but not `f(1, 2)`).

A named pattern is expressed as an identifier followed by the equal sign (i.e., `=`) and a positional pattern.
For example, the pattern `f(a = x, b = x)` matches any call to a function `f` with two named arguments `a` and `b` having the same value (e.g., `f(a = 1, b = 1)` but not `f(a = 1, b = 2)`).

A call pattern successfully matches a call observation if and only if each argument of the call is matched by a different argument pattern, and all argument patterns have been matched.
Naturally, the order in which positional arguments also has to match the order in which positional patterns are laid out.
For example, `f(x, b = _)` does **not** match `f(1, b = 2, c = 3)` because the last named argument is not matched by any argument pattern.
Likewise, the `f(x, y)` does **not** match `f(1)` because the last argument pattern has not been matched.

Both positional and named patterns can be declared variadic to match arbitrary numbers of aguments.
A variadic positional pattern is expressed by one star (i.e., `*`) and a variadic named named pattern with two stars (i.e., `**`).
For example, `f(*)` matches (among others) `f()`, `f(1)`, and `f(1, 2)` and `f(**)` matches (among others) `f()`, `f(a = 1)`, and `f(a = 1, b = 2)`.
Note that a variadic positional pattern does not match any named argument, and vice versa.
For example, `f(**)` does not match `f(1)`.

Variadic patterns can be optionally prefixed by a simple identifier to bind the sequence of arguments that has been matched in query filters.
For example, the query `f(xs*) where xs.all(x => x == 0)` matches any call to a function `f` whose all arguments equal to zero, which includes (among others) `f()` and `f(0, 0)` but not `f(0, 1)`.

Finally, the universal pattern `...` can be used instead of a comma-separated list of argument pattern to match any argument list.
For instance, `f(...)` matches (among others) `f()`, `f(1, 2)` and `f(1, b = 2)`.


### Where Clauses

> Work on the interpreter is ongoing; some features are currently unimplemented.

A where clause is an expression that further filters the results of a query by excluding successful that do not satisfy some critera.
For example, consider the query `f(x) where x != 0`, which matches calls to `f` having a single argument different from zero.
The expression `x != 0` is evaluated for each call observation matching the pattern `f(x)`.

A where clause is satisfied if it evaluates to a "truthy" value, which is any value different from `none`, zero, an empty string, an empty array, or an empty table.
If the evaluation of a where clause fails for any of the matching observations (e.g., because it divides by zero or selects an element of a value that is not an array), the query fails and the error is reported.
It is expressed as an expression that can mentions the names bound in call patterns.
The grammar of legal expressions is given below:

```
expr ::=
  infix-expr

infix-expr ::=
  prefix-expr operator expr
  prefix-expr

prefix-expr ::=
  operator compound-expr
  compound-expr

compound-expr ::=
  identifier '=>' expr
  primary-expr compound-expr-tail
  primary-expr

compound-expr-tail ::=
  '(' argument-list ')'
  '(' ')'
  '[' expr ']'
  '.' identifier

primary-expr ::=
  'none'
  boolean-literal
  integer-literal
  floating-point-literal
  string-literal
  identifier
  'if' expr 'then' expr 'else' expr
  '(' expr ')'

argument-list ::=
  expr ',' argument-list
  expr
```

The following operators are supported, from the loosest to the tightest binding:

- `||` and `&&`, which evaluate their right operand only if the left one does not determine their result;
- `<`, `<=`, `>`, and `>=`, which compare two integers or two floating-point numbers;
- `==` and `!=`, which also compare two strings, arrays, tables, functions, or objects by contents, and can compare any value with `none` (e.g., `x == none` holds iff `x` is `none`);
- `+`, `-`, `*`, and `/`, which compute on two integers or two floating-point numbers, failing on overflows and divisions by zero;
- `|`, `^`, and `&`, which compute the bitwise or, exclusive or, and and of two integers, `|` and `^` binding as tightly as `+` and `-`, and `&` as `*` and `/`;
- the prefix operators `!`, which negates the truthiness of its operand, and `-`, which negates a number.

A lambda `x => e` can be applied to one argument, as in `(x => x > 0)(y)`.
Arrays have the following methods, where `p` is a lambda:

- `xs.all(p)` returns whether `p` returns a truthy value for all elements of `xs`, as in `xs.all(x => x == 0)`;
- `xs.any(p)` returns whether `p` returns a truthy value for at least one element of `xs`;
- `xs.count(p)` returns the number of elements of `xs` for which `p` returns a truthy value;
- `xs.len()` returns the number of elements of `xs`.

Tables also have a method `len`, which returns their number of entries.
