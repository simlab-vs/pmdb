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
| `show $N` | Prints the observations in `$N`, with the source code around each of them unless the output is brief (see below). |
| `show variables` | Lists the variables defined so far. |
| `show functions` | Lists the functions whose calls are recorded in the loaded traces, with their numbers of calls. |
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
- `--brief` makes `show` print one line per observation, without the source code around it, and `--non-brief` makes it print the source code. By default, the output is brief iff it isn't written to a terminal; if both flags are given, the last one applies;
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
| `f(x) raised e where e.type == "KeyError"` | calls to `f` that raised a `KeyError` |
| `invoice(o) where o.has("coupon") && o.coupon == "BIG50"` | calls whose argument is a table with `coupon` equal to `"BIG50"` |
| `/Parser\..*/(...)` | calls to the methods of `Parser` |
| `/.*\$exception/` | snaps recording exceptions |
| `f(x) from $0 where x == 0` | the calls in `$0` whose argument is 0 |

> The query language is still evolving, and its syntax and features may change.

### Patterns

A **snap pattern** matches the label of snaps.
It is an identifier, a regular expression enclosed in slashes (e.g., `/.*\$result/`), or the wildcard `_`.

Labels are strings, and a pattern must match a whole label.
Their forms depend on how snaps were recorded:

- `<function>.$result` labels the snap holding the value returned by a call to `<function>`, e.g. `total.$result`, or `Cart.add.$result` for a method;
- `<function>.$exception` labels the snap holding the exception raised by a call to `<function>`, a table with its `type` and `message`;
- a snap recorded explicitly has the label given by the program, e.g. `total` for `recorder.main.snapshot("total", t)` in Python.

Since `.` and `$` can't appear in identifiers, labels of the first two forms are matched with regular expressions, such as `/total\.\$result/`, `/.*\$exception/` or `/Cart\..*\$result/`.
To select calls by their outcomes rather than the snaps recording them, use outcome patterns (below).

A **call pattern** has the form `<identifier-pattern>(<argument patterns>)`, where the identifier pattern matches the name of the function and the argument patterns, separated by commas, match the arguments.
Identifiers and regular expressions must match the *whole* name.
Python methods are recorded with their qualified names (e.g., `Parser.take`), so they are matched with regular expressions such as `/Parser\.take/` or `/.*\.take/`.
When a query selects nothing because its identifier pattern matches no recorded function, `pmdb` says so in a warning that names the recorded functions it partially matches: those whose names end with `.` and the identifier (`take` for `Parser.take`), or that contain a match of the regular expression.

Argument patterns are positional or named:

- A **positional pattern** is a wildcard (`_`), a variable, or a literal.
  A variable is any name that isn't a literal (e.g. `x`, `order`, or `E0`): it matches any value and binds the name to that value, so that the where clause can use it, as in `f(x) where x > 1`.
  Repeated occurrences of the same variable must match equal values: `f(x, x)` matches `f(1, 1)` but not `f(1, 2)`.
  To match a string, write it in double quotes: `f(E0)` matches any argument and binds `E0`, whereas `f("E0")` matches the string `"E0"`.
  A literal is a Boolean, an integer, a floating-point number, a string in double quotes, or `none`, and matches only equal values, as compared by `==`: `f(1, "a")` matches `f(1, "a")` and `f(1.0, "a")`, but not `f("1", "a")`.
- A **named pattern** is a label followed by `=` and a positional pattern: `f(a = x, b = x)` matches `f(a = 1, b = 1)` but not `f(a = 1, b = 2)`.
- A **variadic positional pattern** (`*`) matches any number of positional arguments, and a **variadic named pattern** (`**`) any number of named arguments.
  Either can be prefixed by a name binding the matched arguments as an array or a table, as in `f(xs*) where xs.all(x => x == 0)`.
  A variadic positional pattern can appear anywhere among positional patterns: `f(*, x)` binds the last positional argument, and `f(1, *, x)` matches calls whose first positional argument is 1 and that have at least two.
  When several variadic positional patterns could split the arguments differently, the first one takes as many as possible.
- The **universal pattern** `...` matches any argument list: `f(...)` matches `f()`, `f(1, 2)`, and `f(1, b = 2)`.
  Among other patterns, `...` matches any further arguments, positional or named, like `*, **`: `f("x", ...)` matches the calls whose first argument is `"x"`.

A call pattern matches a call if and only if each argument of the call is matched by a different argument pattern and every argument pattern is matched, with positional patterns matching positional arguments in order.
For example, `f(x, b = _)` doesn't match `f(1, b = 2, c = 3)`, because `c` isn't matched, and `f(x, y)` doesn't match `f(1)`, because `y` isn't matched.

A call pattern can be followed by an outcome pattern, which filters calls by how they ended:

- an arrow (`->`) followed by a positional pattern matches the calls that returned a value matching that pattern.
  For example, `f(x) -> r where r > x` matches the calls to `f` returning a value greater than their argument, and `f(x) -> x` matches those returning their argument;
- `raised` followed by a positional pattern matches the calls that raised an exception matching that pattern, the exception being the table with the `type` and the `message` that is recorded for it.
  For example, `f(x) raised e where e.type == "KeyError"` matches the calls to `f` that raised a `KeyError`, and `f(...) raised _` all the calls to `f` that raised.

Outcome patterns only match calls whose outcome has been recorded, so `->` never matches calls that raised and `raised` never matches calls that returned.

### Sources

A from clause restricts a query to the observations of a variable or of another query, as in `f(x) from $0` or `f(x) from select f(...) -> 0`.
It only searches these observations, not the observations made during the calls they contain.
Without a from clause, a query searches all observations of all loaded traces.

### Where clauses

A where clause is an expression evaluated for each match, in which the names bound by the pattern are defined: the variables of its argument patterns (`x` in `f(x)`), of its outcome pattern (`r` in `-> r`, `e` in `raised e`), and of its variadic patterns (`xs` in `xs*`).
A snap pattern binds no name.
A match is kept if the expression evaluates to `true`.
The expression, like every condition (the operands of `!`, `&&`, and `||`, the condition of `if`, and the results of the lambdas passed to `all`, `any`, and `count`), must evaluate to a Boolean: `where x` fails if `x` is a number, whereas `where x != 0` doesn't.
If the evaluation fails for any match (e.g., because it divides by zero, selects a property that a table doesn't have, or compares a number with a string), the query fails and the error is reported.

The operators, from the loosest to the tightest binding, are:

- `||` and `&&`, which compute the disjunction and conjunction of two Booleans, evaluating their right operand only if the left one doesn't determine their result;
- `<`, `<=`, `>`, and `>=`, which compare two numbers;
- `==` and `!=`, which also compare two Booleans, strings, arrays, tables, functions, or objects by contents, and can compare any value with `none` (e.g., `x == none` holds iff `x` is `none`);
- `+`, `-`, `*`, and `/`, which compute on two numbers, failing on divisions by zero;
- `|`, `^`, and `&`, which compute the bitwise or, exclusive or, and and of two numbers with integral values, or the same operations on two Booleans without short-circuiting, `|` and `^` binding as tightly as `+` and `-`, and `&` as `*` and `/`;
- the prefix operators `!`, which negates a Boolean, and `-`, which negates a number.

Integers and floating-point numbers are both numbers, compared by value: `0 == 0.0` and `1 < 1.5` hold, but `9007199254740993 == 9007199254740992.0` doesn't.
Floating-point numbers follow IEEE 754, so NaN is neither less than, equal to, nor greater than any number, itself included.
Integers have arbitrary precision, so they never overflow.
`+`, `-`, and `*` compute an integer from two integers, and a floating-point number otherwise; `/` always computes a floating-point number (`7 / 2 == 3.5`).
An integer is converted to a floating-point number only if it has an exact floating-point representation, and the operation fails otherwise (e.g., `9007199254740993 + 0.5` fails).
Likewise, the bitwise operators convert a floating-point number to an integer only if it has an exact 64-bit integer representation (e.g., `2.0 | 1 == 3`, but `2.5 | 1` fails).

Comparisons and logical operators evaluate to the Booleans `true` and `false`, which are distinct from integers: `true == 1` and `true + 1` fail, but `int(true) + 1 == 2` holds.

Elements of arrays are selected with `xs[i]`, and properties of tables with `t.name`.
A lambda `x => e` can be applied to one argument, as in `(x => x > 0)(y)`.
Arrays and tables have the following methods, where `p` is a lambda:

- `xs.all(p)` returns whether `p` returns `true` for all elements of `xs`;
- `xs.any(p)` returns whether `p` returns `true` for at least one element of `xs`;
- `xs.count(p)` returns the number of elements of `xs` for which `p` returns `true`;
- `xs.len()` and `t.len()` return the number of elements of `xs` and of entries of `t`;
- `t.has(k)` returns whether the table `t` has an entry whose key is the string `k`. Applying `has` to a value that isn't a table, or with a key that isn't a string, is an error.

`t.has` makes it possible to filter on properties that only some tables have: `o.has("coupon") && o.coupon == "BIG50"` holds for the tables whose `coupon` is `"BIG50"`, without failing on those without `coupon`.

Two predefined functions convert between Booleans and numbers, which are never converted implicitly:

- `int(b)` returns `1` if the Boolean `b` is `true`, and `0` otherwise;
- `bool(n)` returns `false` if the number `n` is zero or NaN, and `true` otherwise.

A variable named `int` or `bool` hides the predefined function.

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
