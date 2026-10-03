---
name: pmdb
description: Debug a Python program by recording a trace of its function calls (arguments, return values, exceptions) and querying it with pmdb, instead of adding prints or stepping through a debugger. Use it whenever a program produces wrong output or a test fails with a wrong value and the cause isn't obvious from the traceback or a quick read, especially when the wrong value comes out of a long call chain, from one input among many, from recursion, or from a computation whose intermediate values you'd otherwise print. Also use it when the user mentions pmdb, traces, or a `.pmdb` file. Skip it when a traceback already points at the faulty line or the code is small enough to check by reading.
---

# Debugging with pmdb

pmdb records a run of a program as a tree of calls, each with its arguments, its result or
exception, and its call site. Queries then check a hypothesis against every call at once, e.g.
"which calls of `line_total` returned something other than quantity × price?", instead of
printing values and re-running. Below, `<this skill>` is the directory containing this file.

## 1. Record the failing run

Record the smallest run that shows the bug, such as one failing input rather than a whole test
suite, so the trace stays small and the answers readable.

`<this skill>/scripts/pmdb-record` runs a Python script and records every function and method
defined in the `.py` files of the script's directory and its packages, without editing them:

```
python3 <this skill>/scripts/pmdb-record -o trace.pmdb main.py input.json
```

- The program runs as usual (same output, same exit status), and the trace is written when it
  exits, even if it raises.
- Run it with the interpreter that has the project's dependencies (e.g. `.venv/bin/python`
  instead of `python3`).
- If `recorder` can't be imported, add the directory `Python` of the pmdb repository to
  `PYTHONPATH` (ask the user where it is if you can't find it).
- Not recorded: lambdas, calls answered by a cache such as `functools.lru_cache`, asynchronous
  generators, and test functions. A generator or coroutine call is recorded when it starts
  running, and the calls it makes appear under it.
- Record one failing test, not a test file: traces of large projects grow fast (tens of
  thousands of calls per test).

To record a failing pytest test, record a driver script placed at the project root:

```
cat > pmdb_driver.py <<'EOF'
import sys
import pytest
sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", "tests/test_x.py::test_y"]))
EOF
python3 <this skill>/scripts/pmdb-record -o trace.pmdb pmdb_driver.py
```

**How Python values are recorded:**

| Python | pmdb |
|---|---|
| `None`, `True`, `False` | `none`, `true`, `false` |
| `int`, `float`, `str` | integer (of any size), floating-point number, string |
| list, tuple | array |
| dict with string keys, named tuple | table, whose fields are read with `t.key` |
| enum member | the string of its name |
| anything else, including class instances, dataclasses and `self` | opaque: `<object>` or its `repr` string, which queries can't look into |

If the state you care about lives in objects, add `def __pmdb__(self): return vars(self)` to
their classes *before* recording, so they're recorded as tables of their fields, and remove it
when you're done.

## 2. Run queries

`pmdb` is a command on your `PATH` (not a Python module, and not one of this skill's scripts).
Pipe commands to it in a quoted heredoc (`'EOF'`), so the shell leaves `$`, `\` and quotes
alone:

```
pmdb trace.pmdb <<'EOF'
select line_total(l) -> t where t != l.quantity * l.price
show $0
EOF
```

- `select <query>` stores its matches in the next variable, `$0` first, then `$1`, and so on, and
  prints their count. `show $N` prints one line per match:
  `file:line: call f(args) -> result` (or `raised {…}`), where `file:line` is the call site.
- `show` takes a variable (`show $0`), not a file. `show functions` lists every recorded function
  with its number of calls: use it first to find exact names, such as `Class.method`.
- The heredoc holds pmdb commands only. Shell pipes go after it, on the `pmdb` line:
  `pmdb trace.pmdb <<'EOF' | head -50`, never `show $0 | head` inside it.
- Variables last for one pmdb invocation, so a `select` and the commands using its result go in
  the same heredoc.
- pmdb stops at the first failing command (exit status 1), so run independent queries in separate
  invocations.
- Arguments print in full, so a big argument (a catalog, a config) fills every line. Shorten long
  lines with `clip`, which keeps the function and the result, and limit the output with `head`:

  ```
  pmdb trace.pmdb <<'EOF' | <this skill>/scripts/clip | head -50
  ```
- `pmdb --show trace.pmdb` prints the whole call tree with results, to see what a call did inside.
  It can be megabytes long, so filter it:

  ```
  pmdb --show trace.pmdb | <this skill>/scripts/clip | grep -n -A 15 'call price(B07'
  ```

## 3. Write queries

A query is a pattern, optionally followed by `from $N` (to search earlier matches only) and
`where <condition>`.

**Patterns.** In `f(x, "B2", _)`:
- A name (`x`) matches any value and binds it for the where clause. So `f(E0)` matches *any*
  argument; to match the string, write `f("E0")`.
- A literal (`10`, `2.5`, `"B2"`, `true`, `none`) matches equal values only, and never fails.
- `_` matches any value without binding it.
- `*` matches any number of positional arguments, `**` any number of named ones, and `...` any
  further arguments: `f(...)` matches every call of `f`, and `f("B2", ...)` those whose first
  argument is `"B2"`. Every argument the call passed must be matched: `f(x)` doesn't match a call
  with two arguments, and pmdb warns when no call has the shape a pattern expects.

After the arguments, `-> r` matches calls that returned, binding `r` to the result, and
`raised e` calls that raised, binding `e` to a table with the exception's `type` and `message`
(`str(exception)`, so a `KeyError`'s message keeps its quotes: `'b'`).

| Question | Query |
|---|---|
| every call of `f` | `select f(...)` |
| every call (including the recorder's own `root()`) | `select _(...)` |
| calls with given arguments | `select rate(10)`, `select f(_, "B2", *)` |
| calls by named argument | `select f(*, code = "BIG50", **)` |
| calls breaking an invariant | `select f(x) -> r where r > x` |
| calls returning a given value | `select f(...) -> none`, `select f(...) -> 0` |
| calls that raised | `select f(...) raised e`, `select _(...) raised e where e.type == "KeyError"` |
| calls on tables (dicts, named tuples) | `select invoice(o) where o.currency == "GBP"` |
| … when the key may be missing | `select invoice(o) where o.has("coupon") && o.coupon == "BIG50"` |
| … with a default value | `select invoice(o) where (if o.has("rate") then o.rate else 0) > 0.2` |
| calls on arrays (lists, tuples) | `select spread(ws) where ws.len() > 1 && ws.any(w => w < 100)` |
| methods (`Class.method`, `self` first) | `select Parser.take(...)`, `select /.*\.take/(...)` |
| nested functions (`outer.<locals>.inner`) | `select /.*inner/(...)` |
| the last positional argument | `select f(*, last)` |
| a subset of earlier matches | `select f(x) from $0 where x > 1` |

Function names match exactly, and a regex (`/…/`) must match the whole name. When a pattern names
no recorded function, pmdb warns and lists the recorded functions it partially matches (e.g.
`Parser.take` for `take`).

`raised` matches every recorded call that raised, including exceptions that were caught and
handled along the way: libraries and Python itself raise and catch many (e.g. `AttributeError`
while looking up attributes). Narrow by function or by `e.type`, and start from the exception the
failing test reports rather than from all of them.

To compare floating-point results with a tolerance, write both differences, since there is no
`abs`: `select total(q, p) -> t where t - q * p > 0.005 || q * p - t > 0.005`.

**Expressions.** `+ - * /`, `< <= > >=`, `== !=`, `&& || !`, `if c then a else b`, `t.key`,
`xs[i]` (no negative indexes: `xs[xs.len() - 1]`), lambdas `x => …`, and the methods `xs.len()`,
`t.len()`, `xs.all(p)`, `xs.any(p)`, `xs.count(p)` and `t.has("key")`. `&&`, `||` and `if`
evaluate only the operands they need, so `o.has("k") && o.k > 0` never reads a missing `k`.
Strings use double quotes. There is no `%`, `//` or `abs`, no `and`/`or`/`not`, no lookup by a
computed key (`t[k]`, `t["key"]`), no chained comparisons (`a < b < c`), no string operations
besides `==`, no array or table literals, and no sums over arrays.

**Values are never converted implicitly, except that integers and floating-point numbers compare
by value:**
- `0 == 0.0` and `1 < 1.5` hold, and `f(...) -> 0` also matches calls returning `0.0`.
- `/` always gives a floating-point number: `7 / 2 == 3.5`.
- NaN is unequal to everything, itself included, so `x != x` finds NaNs.
- Nothing tells an integer from a floating-point number of the same value; `export` keeps the
  distinction (`1` and `1.0`).
- A condition (the where clause, the operands of `&& || !`, the condition of `if`, the result of
  a lambda given to `all`, `any` or `count`) must be a Boolean: `where r` fails when `r` is a
  number. Write `r != 0`, `r != none`, `s != ""` or `xs.len() > 0`.
- `< <= > >=` and arithmetic take numbers only. `==` and `!=` compare two values of the same
  type, two numbers, or anything with `none`: `"1" == 1`, `true == 1` and `true + 1` fail.
- To convert explicitly, `int(b)` turns a Boolean into `1` or `0`, and `bool(n)` a number into
  `false` if it is zero or NaN (unlike Python, where NaN is true), and `true` otherwise.

**One failing evaluation fails the whole query**, so a where clause must work for every call the
pattern matches. Typical failures:
- a key missing from one table (`o.coupon`): guard with `o.has("coupon") && …`, knowing that
  `has` itself fails on values that aren't tables;
- a value whose type varies across calls, e.g. `x == "B2"` or `x > 0` when `x` is sometimes a
  string and sometimes a number: put the literal in the pattern instead (`f("B2")`), or narrow
  the pattern first and filter `from $N`;
- `none` where a number is expected (`r > 0`): write `r != none && r > 0`;
- a division by zero, or arithmetic mixing a floating-point number with an integer too large to
  convert exactly (above 2^53).

**Snaps.** A call's result is also stored as a snap labeled `<function>.$result`, matched by
`select /f\.\$result/`; outcome patterns (`-> r`) are simpler.

**Counting, summing and grouping** are beyond the query language: select the calls, `export`
them, and finish in Python. `export $0 to "calls.jsonl"` writes one JSON object per call, with its
`location`, `function`, `positional` and `named` arguments and the value it `returned` or the
exception it `raised`, all typed:

```
pmdb trace.pmdb <<'EOF'
select ship(order, carrier) where carrier != "post"
export $0 to "shipments.jsonl"
EOF
python3 -c '
import collections, json
calls = [json.loads(l) for l in open("shipments.jsonl")]
print(collections.Counter(c["positional"][0]["customer"] for c in calls).most_common(5))'
```

This is much smaller and faster than printing calls with `show` and parsing them.

**When you are handed a trace of a failing run** (rather than recording one), start from what
it can tell that the code can't: `show functions` gives each function's number of calls, which
you can compare with the counts in the report (e.g. one more call than there are orders); and the values
in the report can often be recomputed from the recorded arguments and results, with `export`, to
find which calls account for a difference.

## 4. What else trips queries up

- **Arguments are recorded as passed.** `f(1, y=2)` has one positional argument and one named
  one (shown as `y: 2`), and omitted defaults are absent, so `f(x, y)` doesn't match it. Start
  with `select f(...)` and `show $0` to see how calls were recorded.
- **Methods count `self` as their first argument**, and their names include the class (see the
  table).
- **Arguments are recorded when the call starts**, results when it returns: a list the call
  mutates shows its old contents in the arguments.
- **Keys that aren't identifiers can't be read**: a key such as `"unit price"` or `"0"` has no
  `t.…` form. Use `t.has("…")` and `show`.
- **`from $N` searches the matched calls only**, not the calls made inside them. To look inside a
  call, use `pmdb --show` (§2).
- **An exception matches every recorded call it passes through**: if `f` calls `g` and `g`
  raises, both `g(...) raised e` and `f(...) raised e` match. `show` points at the line calling
  the raising function, not at the `raise`.
- **Values print without quotes**: `call f(B2)` is a call with the string `"B2"`, `1` may be the
  string `"1"`, `f()` may be a call with an empty string, and `"a, b"` looks like two arguments.
  `export` writes typed values when it matters.
