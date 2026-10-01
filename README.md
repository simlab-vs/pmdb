# pmdb

`pmdb` is a language-agnostic *post-mortem* debugger.
Instead of stepping through a running program, you record a trace of its execution and then ask questions about that trace, such as "which calls to `parse` returned an empty list?" or "which orders were billed in GBP?".

Unlike a traditional live debugger, a post-mortem debugger works on traces, after the program has finished running.
This is related to, but different from, [time-travel debugging](https://en.wikipedia.org/wiki/Time_travel_debugging), which extends a live debugger with the ability to go back to a previous state.

- [Quick start](#quick-start)
- [Recording traces](#recording-traces)
- [Exploring traces](#exploring-traces)
- [Query language](#query-language)
- [Using pmdb from coding agents](#using-pmdb-from-coding-agents)

## Quick start

`pmdb` is written in Swift.
[Install Swift](https://www.swift.org/install/), clone this repository, and build `pmdb`:

```
swift build -c release
```

The executable is written to `.build/release/pmdb`.

Then record a trace of a program.
With the Python recorder (in [Python](Python)), decorate the functions you want to observe:

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

Every call to a decorated function is recorded, so evaluating `factorial(3)` records 3 calls (`pmdb.main.run` simply applies a function to the given arguments).
The trace is a tree of calls, which `pmdb --show` prints with the value each call returned:

```
$ pmdb --show factorial.trace
* call root()
└─* call factorial(3) -> 6
  └─* call factorial(2) -> 2
    └─* call factorial(1) -> 1
```

Finally, query the trace in an interactive session:

```
$ pmdb factorial.trace
(pmdb) select factorial(x) where x > 1
$0 = <2 element(s) in 1 trace(s)>
(pmdb) show $0
factorial.py:8: call factorial(3) -> 6
     6 |
     7 | if __name__ == "__main__":
>    8 |   n = pmdb.main.run(factorial, 3)
     9 |   print(n)  # Prints 6
    10 |
continue? [Y/n] n
(pmdb) exit
```

## Recording traces

A trace is not a sequence of executed statements but a collection of *observations* about the execution, structured as a tree whose nodes are call frames: each child of a call is an observation made during that call.
There are two kinds of observations:

- a **call** records the name of the function being called, the values of its arguments when the call started, and the location of the call site;
- a **snap** records a value with an optional label.

Each recorded call is followed by a snap labeled `<function>.$result`, holding the value it returned, or `<function>.$exception`, holding a table with the `type` and the `message` of the exception it raised.
`pmdb` shows these outcomes next to the calls (`-> 6`, or `raised {message: …, type: KeyError}`).
Snaps can also be recorded explicitly, e.g. with `pmdb.main.snapshot("label", value)` in Python.

`pmdb` is language-agnostic, but a program must be instrumented to produce a trace.
Recorders are available for Python and Rust, and traces can also be written as XML (see [Documentation/Traces.md](Documentation/Traces.md)).

### Python

The recorder in [Python](Python) records calls to the functions decorated with `@pmdb.main.record`, as shown in the [quick start](#quick-start).
Arguments, results, and snaps are recorded in the state they have when they are observed:

- `None` is recorded as `none`, and `True` and `False` as Booleans;
- lists and tuples are recorded as arrays, and dictionaries with string keys and named tuples as tables;
- members of enumerations are recorded as their names;
- a class can choose how its instances are recorded by defining a method `__pmdb__` returning the value to record instead, and `pmdb.register(cls, convert)` does the same for classes one cannot modify;
- other objects are pickled, or recorded as the string returned by `repr` if they cannot be pickled.

To record every function of a program without editing it, use [`skills/pmdb/scripts/pmdb-record`](skills/pmdb/scripts/pmdb-record):

```
PYTHONPATH=path/to/pmdb/Python skills/pmdb/scripts/pmdb-record -o trace.pmdb main.py input.json
```

### Rust

The recorder in [Rust](Rust) records the functions annotated with `#[pmdb::record]`:

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

## Exploring traces

`pmdb` takes the traces to explore as arguments and reads commands from its standard input:

| Command | Effect |
|---|---|
| `select <query>` | Runs a [query](#query-language) and assigns its result to the next variable `$0`, `$1`, … |
| `show $N` | Prints the observations in `$N`, with the source code around each of them. |
| `show variables` | Lists the variables defined so far. |
| `load <path> as $name` | Loads another trace. |
| `exit` | Ends the session. |

When the standard input is a terminal, the session is interactive: `pmdb` prompts for commands, asks whether to continue after each observation it shows, and reports errors without exiting.
Otherwise, `pmdb` runs the commands it reads, one per line, and exits, which makes it easy to script:

```
pmdb factorial.trace <<'EOF'
select factorial(x) where x > 1
select _(...) from $0
show $1
EOF
```

In that case, `pmdb` doesn't print prompts, `show` prints all observations without asking to continue, and `pmdb` stops at the first command that fails, exiting with a non-zero status.
A command can span several lines if each line but the last ends with a backslash.
Comments start with `#` and extend to the end of the line.

Several traces can be loaded at once, in which case queries select observations from all of them.

Other options:

- `pmdb --show <traces>` prints traces as trees and exits;
- `pmdb --export-xml <trace>` prints a trace in the XML format described in [Documentation/Traces.md](Documentation/Traces.md). `pmdb` loads traces whose names end with `.xml` as XML documents.

## Query language

A query has the following form:

```
<pattern> [from <source>] [where <expression>]
```

The pattern selects calls or snaps, the optional from clause restricts the observations the query searches, and the optional where clause filters the matches with a Boolean condition.
Some examples:

| Query | Selects |
|---|---|
| `f(...)` | all calls to `f` |
| `f(x) where x > 1` | calls to `f` with one argument greater than 1 |
| `f(10, "a")` | calls to `f` whose arguments are `10` and `"a"` |
| `f(x, *)` | calls to `f` with at least one positional argument |
| `f(*, code = "BIG50", **)` | calls to `f` with a named argument `code` equal to `"BIG50"` |
| `f(x) -> r where r < x` | calls to `f` that returned less than their argument |
| `f(...) -> none` | calls to `f` that returned `none` |
| `invoice(o) where o.has("coupon") && o.coupon == "BIG50"` | calls whose argument is a table with `coupon` equal to `"BIG50"` |
| `/Parser\..*/(...)` | calls to the methods of `Parser` |
| `/.*\$exception/` | snaps recording exceptions |
| `f(x) from $0 where x == 0` | the calls in `$0` whose argument is 0 |

> The query language is still evolving, and its syntax and features may change.

### Patterns

A **snap pattern** matches the label of snaps.
It is an identifier, a regular expression enclosed in slashes (e.g., `/.*\$result/`), or the wildcard `_`.

A **call pattern** has the form `<identifier-pattern>(<argument patterns>)`, where the identifier pattern matches the name of the function and the argument patterns, separated by commas, match the arguments.
Identifiers and regular expressions must match the *whole* name.
Python methods are recorded with their qualified names (e.g., `Parser.take`), so they are matched with regular expressions such as `/Parser\.take/` or `/.*\.take/`.

Argument patterns are positional or named:

- A **positional pattern** is a wildcard (`_`), a variable, or a literal.
  A variable matches any value and binds it, and repeated occurrences of the same variable must match equal values: `f(x, x)` matches `f(1, 1)` but not `f(1, 2)`.
  A literal is a Boolean, an integer, a floating-point number, a string in double quotes, or `none`, and matches only equal values: `f(1, "a")` matches `f(1, "a")` but not `f(1.0, "a")`, since an integer is never equal to a floating-point number.
- A **named pattern** is a label followed by `=` and a positional pattern: `f(a = x, b = x)` matches `f(a = 1, b = 1)` but not `f(a = 1, b = 2)`.
- A **variadic positional pattern** (`*`) matches any number of positional arguments, and a **variadic named pattern** (`**`) any number of named arguments.
  Either can be prefixed by a name binding the matched arguments as an array or a table, as in `f(xs*) where xs.all(x => x == 0)`.
- The **universal pattern** `...` matches any argument list: `f(...)` matches `f()`, `f(1, 2)`, and `f(1, b = 2)`.

A call pattern matches a call if and only if each argument of the call is matched by a different argument pattern and every argument pattern is matched, with positional patterns matching positional arguments in order.
For example, `f(x, b = _)` doesn't match `f(1, b = 2, c = 3)`, because `c` isn't matched, and `f(x, y)` doesn't match `f(1)`, because `y` isn't matched.

A call pattern can be followed by an arrow (`->`) and a positional pattern matching the value returned by the call.
For example, `f(x) -> r where r > x` matches the calls to `f` returning a value greater than their argument, and `f(x) -> x` matches those returning their argument.
Such a pattern only matches calls whose result has been recorded, so it never matches calls that raised an exception.

### Sources

A from clause restricts a query to the observations of a variable or of another query, as in `f(x) from $0` or `f(x) from select f(...) -> 0`.
It only searches these observations, not the observations made during the calls they contain.
Without a from clause, a query searches all observations of all loaded traces.

### Where clauses

A where clause is an expression evaluated for each match, in which the names bound by the pattern are defined.
A match is kept if the expression evaluates to a *truthy* value, which is any value other than `none`, `false`, zero, an empty string, an empty array, or an empty table.
If the evaluation fails for any match (e.g., because it divides by zero, selects a property that a table doesn't have, or compares an integer with a floating-point number), the query fails and the error is reported.

The operators, from the loosest to the tightest binding, are:

- `||` and `&&`, which evaluate their right operand only if the left one doesn't determine their result;
- `<`, `<=`, `>`, and `>=`, which compare two integers or two floating-point numbers;
- `==` and `!=`, which also compare two Booleans, strings, arrays, tables, functions, or objects by contents, and can compare any value with `none` (e.g., `x == none` holds iff `x` is `none`);
- `+`, `-`, `*`, and `/`, which compute on two integers or two floating-point numbers, failing on overflows and divisions by zero;
- `|`, `^`, and `&`, which compute the bitwise or, exclusive or, and and of two integers, or the same operations on two Booleans without short-circuiting, `|` and `^` binding as tightly as `+` and `-`, and `&` as `*` and `/`;
- the prefix operators `!`, which negates the truthiness of its operand, and `-`, which negates a number.

Comparisons and logical operators evaluate to the Booleans `true` and `false`, which are distinct from integers: `true == 1` and `true + 1` fail.

Elements of arrays are selected with `xs[i]`, and properties of tables with `t.name`.
A lambda `x => e` can be applied to one argument, as in `(x => x > 0)(y)`.
Arrays and tables have the following methods, where `p` is a lambda:

- `xs.all(p)` returns whether `p` returns a truthy value for all elements of `xs`;
- `xs.any(p)` returns whether `p` returns a truthy value for at least one element of `xs`;
- `xs.count(p)` returns the number of elements of `xs` for which `p` returns a truthy value;
- `xs.len()` and `t.len()` return the number of elements of `xs` and of entries of `t`;
- `t.has(k)` returns whether the table `t` has an entry whose key is the string `k`. Applying `has` to a value that isn't a table, or with a key that isn't a string, is an error.

`t.has` makes it possible to filter on properties that only some tables have: `o.has("coupon") && o.coupon == "BIG50"` holds for the tables whose `coupon` is `"BIG50"`, without failing on those without `coupon`.

The grammar of expressions is:

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

String literals are enclosed in double quotes and support the escape sequences `\n`, `\t`, `\\`, and `\"`.

## Using pmdb from coding agents

[skills/pmdb](skills/pmdb) is a skill for coding agents such as Claude Code.
It explains how to record traces, how to query them in one command, recipes for common debugging questions, and the pitfalls agents ran into in our [usability study](bench/usability/round-1/results/REPORT.md).
To install it for Claude Code, copy or link the directory into `~/.claude/skills/` (for all projects) or `.claude/skills/` (for one project).
