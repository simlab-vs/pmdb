---
name: pmdb
description: Debug a Python program by recording every call it makes (arguments, return values, exceptions) and querying the recording in Python, instead of adding prints or stepping through a debugger. Use it whenever a program produces wrong output or a test fails with a wrong value and the cause isn't obvious from the traceback or a quick read, especially when the wrong value comes out of a long call chain, from one input among many, or from a computation whose intermediate values you'd otherwise print, and whenever you are given a recorded trace (a `.pmdb` file) of a run. Also use it when the user mentions pmdb or traces. Skip it when a traceback already points at the faulty line or the code is small enough to check by reading.
---

# Debugging with pmdb

pmdb records a run of a Python program as a tree of calls: each call of the program's own
functions, with its arguments, its result or exception, its caller and the calls it made. You
then query the recording with the Python package `recorder`, to check a hypothesis against
every call at once ("which calls of `line_total` returned something other than quantity ×
price?") instead of printing values and re-running. Below, `<this skill>` is the directory
containing this file.

`recorder` is importable as is: `python3 -c 'import recorder'` should succeed. Only if it
doesn't, add the directory `Python` of the pmdb repository to `PYTHONPATH`; other copies of
`recorder` found on disk can be older versions.

## Recording a run

If you were handed a trace, skip to the next section.

```
python3 <this skill>/scripts/pmdb-record -o trace.pmdb main.py input.json
python3 <this skill>/scripts/pmdb-record -o trace.pmdb -m pytest -q tests/test_x.py::test_y
```

- Every call of a function or method defined in a `.py` file under the current directory is
  recorded (test functions included), but not code in installed packages or the standard
  library, nor lambdas and comprehensions. `--root DIR` (repeatable) records the functions under
  `DIR` instead. Files aren't modified.
- The program runs as usual (same output, same exit status), and the trace is written when it
  exits, even if it raises. Run it with the interpreter that has the project's dependencies
  (e.g. `.venv/bin/python` instead of `python3`).
- Record the smallest run that shows the bug, such as one failing test: projects make tens of
  thousands of calls per test, and the trace grows with them.
- To record part of a program, from Python: `with recorder.recording("trace.pmdb"): run()`.

**Snaps.** To record a value that isn't an argument or result (a local variable, an
intermediate total), add `recorder.snap("label", value)` to the code and record again. It
returns `value` (so `total = recorder.snap("total", a + b)` works) and does nothing when the
program isn't being recorded. Remove snaps when you're done.

## Querying a trace

Load the trace once per script (it takes a few seconds for tens of megabytes) and ask several
questions in it:

```
python3 - <<'EOF'
import recorder
from recorder import Q
t = recorder.load("trace.pmdb")
print(t.functions())                     # every recorded function and its number of calls
bad = t.calls("post", raised="ValueError").first()
print(bad, bad.path())                   # the call, and the calls it was made in, outermost first
print(bad["txn"], bad.caller["day"])     # arguments by parameter name
t.calls("post", before=bad, where=lambda c: c["txn"]["account"] == bad["txn"]["account"]).show()
t.calls("post", caller=Q("close_month", where=lambda c: c["day"] == 31)).show()
print(t.calls("post", returned=True).count_by(lambda c: c["txn"]["account"]))
EOF
```

When the analysis grows, keep loading and helper functions in a file (e.g. `analysis.py`) and
import it from each new script, rather than pasting them again.

**Selecting calls.** `t.calls(*selectors, **conditions)` returns the calls (a `Calls` list, in
the order they started) matching every selector and condition. A selection can be narrowed
with `.where(*selectors, **conditions)`, which takes the same arguments.

Selectors:
- `"post"`: calls of a function by name; `"post"` also matches `Ledger.post`, and
  `"Ledger.post"` only that method (`t.functions()` lists the names);
- `re.compile(r"Ledger\..*")`: names matching a regular expression;
- a predicate on calls, such as `lambda c: c["amount"] < 0`;
- a call, or a list of calls;
- `Q(*selectors, **conditions)`: a reusable selection, combined with `&`, `|` and `~`, e.g.
  `t.calls(Q("post") & ~Q(ancestor="replay"))`.

Conditions:

| condition | holds for a call that |
|---|---|
| `where=pred` | satisfies `pred` |
| `returned=True` / `=value` / `=pred` | returned (a value equal to `value`, or satisfying `pred`) |
| `raised=True` / `="KeyError"` / `=pred` | raised (an exception of that type, or satisfying `pred`) |
| `caller=sel` | was made directly by a selected call |
| `callee=sel` | made a selected call directly |
| `ancestor=sel` | was made during a selected call, directly or not |
| `descendant=sel` | made a selected call, directly or not |
| `before=sel` / `after=sel` | started before a selected call started / after one ended |

`True` and `False` (`returned=False`) test only whether the call returned or raised.

**Calls.** A call `c` has:
- `c["name"]`: the argument of a parameter, by name (`c["self"]` for methods), or by position
  (`c[0]`); `c.get("name")` returns `None` if there's no such parameter; `c.params` is the dict
  of all of them. Arguments are recorded as they were when the call started.
- `c.function` (qualified, e.g. `Ledger.post`), `c.location` (the call site's file and line),
  `c.definition` (where the function is defined), `c.index` (shown as `#index`, for
  `t.call(index)`).
- `c.returned` and `c.raised` (Booleans), `c.result`, `c.exception` (with `type` and `message`).
- `c.caller`, `c.callees(...)`, `c.ancestors(...)` (innermost first), `c.ancestor(...)` (the
  innermost selected one), `c.descendants(...)`, `c.path()`; the methods take selectors and
  conditions.
- `c.snaps(label)` (`deep=True` to include the calls made during it), and `c.tree(depth=3)`,
  which prints the call and the calls made during it.

**Selections.** `Calls` is a list, with `first()` and `last()` (or `None`), `one()`, `count()`,
`values(key)`, `group_by(key)` (a dict of selections), `count_by(key)` (a `Counter`),
`functions()`, `show(limit=20)`, and `|`, `&`, `-` between selections. A key is a parameter
name or a function on calls. `t.roots()` are the calls made at the top level (one per thread),
and `t.snaps(label)` the snaps, each with `label`, `value` and `call`.

**Values** are Python values:
- `None`, Booleans, numbers and strings as themselves;
- lists and tuples as lists;
- dicts with string keys and named tuples as dicts: `c["txn"]["amount"]`, not `.amount`;
- enum members as the strings of their names;
- other objects (class instances, dataclasses, sets) as `Opaque` values, shown as `<Ledger>`,
  whose `.unpickle()` rebuilds the object (the program's modules must be importable, e.g. with
  its directory on `sys.path`); objects that can't be pickled are recorded as their `repr`
  string.

To query the fields of your own objects, define `def __pmdb__(self): return vars(self)` in their
class before recording: they're then recorded as dicts of their fields.

**Errors.** A predicate that raises stops the query with a `QueryError` naming the call it
raised on, e.g. when a parameter doesn't exist (the error lists the call's parameters) or a value
is `None`; handle that case in the predicate (`c.get("name")`). An unknown function name raises
a `QueryError` too.

## When you are handed a trace of a failing run

The trace holds what the code and the logs don't: the actual inputs, every intermediate result,
and how many times each function ran. `t.functions()` gives the counts, which you can compare
with those in the report (e.g. one more call than there are orders), and the figures in the
report can often be recomputed from recorded arguments and results, to find which calls account
for a difference. The same recomputation, applied to your fix (e.g. calling the fixed function
on recorded arguments), checks the fix against the figures that were reported.

## What trips queries up

- **An exception is recorded on every call it passes through**: if `f` calls `g` and `g`
  raises, both `f` and `g` have `raised` set. `c.callees(raised=True)` is empty for the call
  that raised it first.
- **Generators and coroutines** are one call each, from when they start running to when they
  finish, with the value they return as their result; calls made by their consumer while they
  are suspended aren't in them.
- **Arguments are recorded when the call starts**: a list or object the call mutates shows its
  old contents in the arguments; the new contents are in later calls' arguments, or in a snap.
- **Default arguments are recorded** with the parameters that received them, so `c["note"]`
  exists even if the caller omitted `note`.
