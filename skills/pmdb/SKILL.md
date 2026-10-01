---
name: pmdb
description: Debug a Python or Rust program by recording a trace of its function calls (arguments and return values) and querying it with pmdb. Use when a bug depends on runtime values that reading the code doesn't reveal, e.g. a wrong result deep in a call chain, a rare input among many calls, or recursion, or when the user mentions pmdb or a `.pmdb` trace. Not worth it when a traceback already points at the faulty line, or when the code is small enough to read in full.
---

# Debugging with pmdb

pmdb answers questions such as "which calls of `f` returned something odd?" over a recorded trace,
instead of stepping through a live program. A trace records every call to the instrumented
functions, with its arguments (at call time), its return value or raised exception, and its call
site, as a tree.

## 1. Record a trace

**Python, without editing the program.** `scripts/pmdb-record` (next to this file) runs a script
and records every function and method defined in the `.py` files of the script's directory:

```
PYTHONPATH=<pmdb repository>/Python <this skill>/scripts/pmdb-record -o trace.pmdb main.py input.json
```

The program runs normally; the trace is written at exit, even if it raises. Record the failing
run, and record a passing run too if you want to compare.

**Python, by hand:** decorate functions with `@recorder.main.record` (`import recorder`), then
`open("trace.pmdb", "wb").write(recorder.main.serialize().buffer)` at the end.

**Rust:** annotate functions with `#[pmdb::record]` (crate `pmdb-recorder`, in `Rust/` of the
repository), then call `pmdb::main().write_to("trace.pmdb")`.

## 2. Query it

Pipe commands to pmdb, one per line. Use a quoted heredoc (`'EOF'`) so the shell leaves `$` and
`\` alone:

```
pmdb trace.pmdb <<'EOF'
select line_subtotal(l) -> s where l.quantity >= 10
show $0
EOF
```

- `select <query>` prints `$N = <k element(s) in 1 trace(s)>` and stores the matches in `$N`
  (`$0`, `$1`, … in order).
- `show $N` prints each match as `file:line: call f(args) -> result`, with the source around the
  call site.
- `pmdb --show trace.pmdb` prints the whole call tree, with results: `call f(3) -> 6`, or
  `raised {message: …, type: KeyError}`. It is large; prefer queries and pipe through `head` or
  `grep` if you need it.
- Variables only exist within one pmdb invocation. Put every command of an investigation in the
  same heredoc. pmdb stops at the first failing command (exit status 1), so later commands don't
  run.

## 3. Query recipes

| To find | Write |
|---|---|
| calls of `f`, any arguments | `select f(...)` |
| calls with a given argument | `select volume_discount_rate(10)` or `select f(_, "B2", y)` |
| calls by named argument | `select f(*, code = "BIG50", **)` |
| calls whose result is odd | `select f(x) -> r where r > x` |
| calls returning a given value | `select f(...) -> 0` |
| calls filtered on table fields | `select invoice(o) where o.currency == "GBP"` |
| … when the field may be missing | `select invoice(o) where o.has("coupon") && o.coupon == "BIG50"` |
| calls on arrays | `select spread(n, ws) where ws.len() > 1 && ws.any(w => w < 100)` |
| methods (recorded as `Class.method`, with `self` first) | `select /Parser\.take/(...)` or `select /.*\.take/(_, "op", *)` |
| exceptions | `select /.*\$exception/` then `show $N` |
| a subset of a previous result | `select f(x) from $0 where x > 1` |

## 4. Pitfalls

- **Names are matched exactly.** Methods are recorded by qualified name, so `take(...)` doesn't
  match `Parser.take`. Use a regex, `/Parser\.take/(...)`. A regex must match the *whole* name.
- **A pattern that doesn't fit the arity matches nothing, silently.** `f(x)` doesn't match a
  call with two arguments; use `f(x, ...)`-style patterns: `f(x, *)`, `f(_, y, **)`, or `f(...)`.
- **Bare names in patterns are variables, not strings.** `f(E0)` binds `E0` to any value; write
  `f("E0")`.
- **Strings use double quotes only**; booleans are `true`/`false`, the null value is `none`.
- **Logical operators are `&&`, `||`, `!`** (not `and`/`or`/`not`). `&`, `|`, `^` are bitwise and
  bind tighter than comparisons: write `(x > 1) & (y > 1)` or use `&&`.
- **`_` can't be used in a where clause**; name the argument instead (`f(x) where x > 0`).
- **One failing evaluation fails the whole query**, e.g. `o.coupon` on a table without `coupon`
  or comparing an integer with a float (`x > 1.0` when `x` is an integer). Guard with `has`,
  match types (`1` vs `1.0`), or narrow the pattern first.
- **`from $N` searches only the observations in `$N`**, not the calls made inside them.
- **Values print without quotes** (`call f(B2)` is the string `"B2"`). Objects the recorder can't
  describe print as `<object>`.
- **Arguments are recorded when the call starts**, results when it returns, so mutations during
  the call show up in the result, not in the arguments.

## 5. A good workflow

1. Run the program and diff its output with the expected one; note the first wrong value.
2. Record the failing run with `pmdb-record`.
3. Find the function that produced the wrong value: `select f(...) -> r where r == <wrong value>`,
   then `show $0` for its arguments and call site.
4. Walk down: query the callees of that function with the arguments you just saw, until a call's
   result is wrong although its arguments are right. That function holds the bug.
5. Fix it, re-run the program, and re-record if you need to confirm the intermediate values.
