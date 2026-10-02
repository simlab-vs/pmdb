---
name: pmdb
description: Debug a Python program by recording a trace of its function calls (arguments, return values, exceptions) and querying it with pmdb, instead of adding prints or stepping through a debugger. Use it whenever a program produces wrong output or a test fails with a wrong value and the cause isn't obvious from the traceback or a quick read, especially when the wrong value comes out of a long call chain, from one input among many, from recursion, or from a computation whose intermediate values you'd otherwise print. Also use it when the user mentions pmdb, traces, or a `.pmdb` file. Skip it when a traceback already points at the faulty line or the code is small enough to check by reading.
---

# Debugging with pmdb

pmdb answers questions like "which calls of `price` returned something other than the sum of their
parts?" over a recorded run, so you check hypotheses against every call at once instead of
printing values and re-running. A trace is a tree of calls to the recorded functions, each with
its arguments (as they were when the call started), its result or exception, and its call site.

## 1. Record the failing run

Record the smallest run that shows the bug: one failing input rather than a whole test suite keeps
the trace small and the answers readable. Traces of tens of thousands of calls with big arguments
reach tens of megabytes; queries stay fast, but their output gets long.

**Python, without editing anything.** `<this skill>/scripts/pmdb-record` runs a script and records
every function and method defined in the `.py` files of the script's directory and its packages:

```
<this skill>/scripts/pmdb-record -o trace.pmdb main.py input.json
```

The program runs as usual (same output, same exit status) and the trace is written at exit, even
if it raises. If `pmdb-record` can't import the recorder, add the directory containing the package
`recorder` (the directory `Python` of the pmdb checkout or installation; ask the user if you can't
find it) to `PYTHONPATH`. Things it doesn't record: lambdas, calls answered by a cache such as
`functools.lru_cache`, and the bodies of generators under their call (a generator call returns at
once, and the calls made while consuming it are attached to the consumer). To record a failing
pytest test, record a driver script at the project root (pmdb-record records the project's
modules; the test functions themselves aren't recorded):

```
cat > pmdb_driver.py <<'EOF'
import sys
import pytest
sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", "tests/test_x.py::test_y"]))
EOF
python3 <this skill>/scripts/pmdb-record -o trace.pmdb pmdb_driver.py
```

Run `pmdb-record` with the interpreter that has the project's dependencies (e.g. the
virtual environment's `python`), as above.

Class instances (including `self`) are recorded as opaque values, which queries can't look into.
If the state you care about lives in objects, add `def __pmdb__(self): return vars(self)` to
their classes *before* recording, so that they're recorded as tables of their fields, and remove
it when you're done.

**Python, by hand:** decorate functions with `@recorder.main.record` (`import recorder`), then
`open("trace.pmdb", "wb").write(recorder.main.serialize().buffer)` at the end.

## 2. Query it

Pipe commands to pmdb, one per line, in a quoted heredoc (`'EOF'`) so the shell leaves `$`, `\` and
quotes alone:

```
pmdb trace.pmdb <<'EOF'
select line_total(l) -> t where t != l.quantity * l.price
show $0
EOF
```

- Each `select <query>` stores its matches in a new variable and prints it, as in
  `$0 = <k element(s) in 1 trace(s)>`. Numbering starts at `$0`: the first `select` of an
  invocation creates `$0`, the second `$1`, and so on. Other commands, `show` included, create
  no variables, so after a single `select`, `show $0` is the only valid `show`.
- `show $N` prints one line per match, `file:line: call f(args) -> result` (or `raised {…}`),
  where `file:line` is the call site; read the source there for context.
- The heredoc holds pmdb commands only; filters go after the redirection:
  `pmdb trace.pmdb <<'EOF' | head -50`.
- Arguments print in full, so a function taking a big structure (a catalog, a config, a parsed
  file) prints all of it on every line. Pipe the output through `<this skill>/scripts/clip`, which
  elides the middle of long lines and keeps the function name and the result, and through `head`
  when you don't know how many lines to expect.
- Variables live for one pmdb invocation only, so a `select` and the `show` or `from $N` using its
  result go in the same heredoc. pmdb stops at the first failing command (exit status 1) and
  skips the rest, so run independent or exploratory queries in separate invocations rather than
  queueing them behind one that may fail.
- `pmdb --show trace.pmdb` prints the whole call tree with results. It's the way to see what a
  given call did inside, but it can be megabytes long, so always filter it:
  `pmdb --show trace.pmdb | <this skill>/scripts/clip | grep -n -A 15 'call price(B07'`.

## 3. Ask questions as queries

A query states what to look for, and can state what *should* hold, so that pmdb lists the calls
where it doesn't.

**Patterns bind variables.** In a call pattern, every name that isn't a literal binds a new
variable to the value it matches, which the where clause can then use: in
`select line_total(l) -> t where t != l.quantity * l.price`, `l` is bound to the argument and `t`
to the returned value. So `f(E0)` matches *any* argument and calls it `E0`; to match the string,
write `f("E0")`. Literals (`10`, `"B2"`, `true`, `none`) match equal values only, and `_`
matches anything without binding it.

**Outcome patterns** filter calls by how they ended: `f(...) -> r` matches the calls that returned,
binding `r` to the value, and `f(...) raised e` the calls that raised, binding `e` to a table with
the exception's `type` and `message`.

| Question | Query |
|---|---|
| every call of `f` | `select f(...)` |
| calls with given arguments | `select rate(10)`, `select f(_, "B2", *)` |
| calls by named argument | `select f(*, code = "BIG50", **)` |
| calls breaking an invariant | `select f(x) -> r where r > x` |
| calls returning a given value | `select f(...) -> none`, `select f(...) -> 0` |
| calls that raised | `select f(...) raised e`, `select _(...) raised e where e.type == "KeyError"` |
| calls on tables (dicts, named tuples) | `select invoice(o) where o.currency == "GBP"` |
| … when the key may be missing | `select invoice(o) where o.has("coupon") && o.coupon == "BIG50"` |
| calls on arrays (lists, tuples) | `select spread(ws) where ws.len() > 1 && ws.any(w => w < 100)` |
| methods (named `Class.method`, `self` first) | `select /Parser\.take/(...)`, `select /.*\.take/(...)` |
| nested functions (`outer.<locals>.inner`) | `select /.*inner/(...)` |
| the last positional argument | `select f(*, last)` |
| a subset of earlier matches | `select f(x) from $0 where x > 1` |

Matches of functions whose arguments are small (`discounted(amount, percent)` rather than
`price(catalog, sku)`) are shorter to read.

**Snaps** hold single values. Their labels are strings, of three forms:
- `<function>.$result`: the value returned by a call to `<function>` (`total.$result`, or
  `Cart.add.$result` for a method);
- `<function>.$exception`: the exception raised by a call, a table with `type` and `message`;
- any label the program chose when recording a snap explicitly
  (`recorder.main.snapshot("total", t)` gives `total`).

A snap pattern must match the whole label, and `.` and `$` need a regular expression:
`select /total\.\$result/`, `select /.*\$exception/`. To find calls by outcome, outcome
patterns are simpler.

**The query language in brief.** Besides the patterns above: `+ - * /` (integer `/` truncates
toward zero, unlike Python's `//`; there is no `%`), `< <= > >=` on numbers, `== !=`, `&& || !`,
`x.field`, `xs[i]` (no negative indexes: `xs[xs.len() - 1]`), and the methods `len()`, `all(p)`,
`any(p)`, `count(p)` (with a lambda `x => …`) and `t.has("key")`. There are no array or table
literals, no string operations besides equality, and no sums or folds over arrays.

**When a check is beyond the query language**, export the trace and finish in Python:
`pmdb --export-xml trace.pmdb > trace.xml` gives every call with typed arguments and results
(`pmdb:call` elements with a `pmdb:function`, `pmdb:arguments` and nested `pmdb:observations`, and
the outcome in the `pmdb:snap` labeled `<function>.$result` that follows the call), which
`xml.etree.ElementTree` reads unambiguously. `show` output is easier to skim but ambiguous to
parse: the string `"1"` and the integer `1` both print as `1`, and `"a, b"` prints like two
arguments.

## 4. What trips queries up

- **Values of different types never compare, not even with `==`.** `r > 0` and `r != 0` fail the
  *whole query* as soon as one `r` is a float (`cannot apply > on values of type 'float' and
  'integer'`), and Python code often returns `0` in one branch and `0.5` in another; a string
  compared with an integer fails the same way. Only `x == none` works on any value. A literal of
  the right type (`r > 0.0`) only helps if every value has that type. Otherwise use truthiness
  (`where r` holds for non-zero numbers and non-empty strings, `where !r` for zero), or literals in
  the pattern, which never fail: `f(x) -> 0` matches only the integer 0, `f(x) -> 0.0` only the
  float.
- **One failing evaluation fails the whole query**, e.g. `o.coupon` on a table without `coupon`.
  Guard with `has`, or narrow the pattern first and filter `from $N`.
- **Arguments are recorded as passed.** `f(1, y=2)` is recorded with a positional argument and a
  named one (shown as `y: 2`), and omitted defaults are absent, so `f(x, y)` doesn't match it.
  Start with `f(...)` or `f(x, *, **)` and look at how calls were actually recorded.
- **Patterns must account for every argument.** `f(x)` silently matches nothing when `f` takes two
  arguments; use `f(x, *)`, `f(*, x)`, `f(_, y, **)` or `f(...)`. `*` matches any number of
  positional arguments wherever it is. Methods count `self` as the first argument.
- **Names match exactly, and a regex must match the whole name.** `take(...)` doesn't match the
  method `Parser.take`; write `/.*\.take/(...)`.
- **Instances of classes are opaque**, dataclasses included. Only dicts with string keys and named
  tuples become tables, and lists and tuples arrays. Other values (class instances, sets,
  `Decimal`, dicts with non-string keys) are recorded as `<object>` or as
  their `repr`, a string such as `<shop.Cart object at 0x…>`, so `self.items` can't be queried and
  fails with `value of type 'string' is not a table`. To see an object's fields, give its class a
  method `def __pmdb__(self): return vars(self)` while you debug; the recorder records what it
  returns instead.
- **Keys that aren't identifiers can't be read**: a dict key such as `"unit price"` or `"0"`
  has no `t.…` form. Use `t.has("…")` and `show`.
- **Syntax:** strings in double quotes only; `true`, `false`, `none`; `&&`, `||`, `!` (not
  `and`, `or`, `not`); `_` only in patterns (name an argument to use it in `where`); `t.k`, not
  `t["k"]`.
- **`from $N` searches the matched calls only**, not the calls made inside them. Use
  `pmdb --show` with `grep -A` to look inside a call.
- **An exception is recorded for every recorded call it passes through**: if `f` calls `g` and
  `g` raises, both `g(...) raised e` and `f(...) raised e` match. `show` points at the line
  calling the raising function, not at the `raise`.
- **Values print without quotes**: `call f(B2)` is the string `"B2"`, and `f()` may be a call with
  an empty string.
- **Arguments are recorded when the call starts**, results when it returns: a list mutated by the
  call shows its old contents in the arguments.
