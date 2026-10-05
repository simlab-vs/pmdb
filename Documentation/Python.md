# Recording and querying traces in Python

The Python package `recorder` (in [../Python/recorder](../Python/recorder)) records traces of
Python programs and queries them in Python. A trace is a tree of the calls a run made:
- each call's arguments, as they were when it started;
- the value it returned, or the exception it raised;
- the call it was made in;
- the values recorded with `recorder.snap`.

The query library selects calls by function, by their values, and by how they relate to other
calls. For example: "the calls of `post` made by a `close_month` call whose `day` is 31", "the
checkouts during which a line total raised", or "the deposits before the failing call with the
same account".

```python
import recorder
from recorder import Q

t = recorder.load("trace.pmdb")
bad = t.calls("line_total", raised=True).one()
t.calls("line_total", ancestor=Q("checkout", where=lambda c: c["code"] == "SAVE10"))
```

Contents:
1. [An example](#an-example)
2. [Recording](#recording)
3. [Selecting calls](#selecting-calls): selectors, conditions, `Q`
4. [Selections](#selections): `Calls`
5. [Calls](#calls): `Call`
6. [Snaps](#snaps)
7. [Values](#values)
8. [Errors](#errors)
9. [What to keep in mind](#what-to-keep-in-mind)
10. [Reference](#reference)

## An example

The examples below query a trace of this program (`shop.py`), which checks out three carts. The
third has a line with quantity 0, which raises; `checkout` turns the exception into `None`.

```python
import collections
import recorder

Line = collections.namedtuple("Line", "sku quantity price")


class Cart:
  def __init__(self, customer):
    self.customer = customer
    self.lines = []

  def add(self, line):
    self.lines.append(line)

  def total(self, discount=0):
    subtotal = sum(line_total(l) for l in self.lines)
    recorder.snap("subtotal", subtotal)
    return round(subtotal * (1 - discount), 2)


def line_total(line):
  if line.quantity <= 0:
    raise ValueError(f"bad quantity for {line.sku}")
  return line.quantity * line.price


def discount_for(code):
  return {"SAVE10": 0.1, "SAVE20": 0.2}.get(code, 0)


def checkout(cart, code=None):
  try:
    return cart.total(discount_for(code))
  except ValueError:
    return None


def main():
  orders = [
    ("ana", [Line("A1", 2, 5.0), Line("B2", 1, 12.5)], "SAVE10"),
    ("bo", [Line("A1", 1, 5.0)], None),
    ("cy", [Line("C3", 0, 7.0), Line("A1", 3, 5.0)], "SAVE20"),
  ]
  for customer, lines, code in orders:
    cart = Cart(customer)
    for line in lines:
      cart.add(line)
    print(customer, checkout(cart, code))
```

`main.py` holds `import shop; shop.main()`. Record it, then load the trace:

```
$ PYTHONPATH=path/to/pmdb/Python skills/pmdb/scripts/pmdb-record -o trace.pmdb main.py
ana 20.25
bo 5.0
cy None
pmdb-record: recorded 22 calls to trace.pmdb
```

```python
>>> t = recorder.load("trace.pmdb")
>>> t
<trace with 22 calls and 2 snaps>
>>> t.functions()
{'Cart.add': 5, 'line_total': 4, 'Cart.__init__': 3, 'checkout': 3, 'discount_for': 3, 'Cart.total': 3, 'main': 1}
>>> t.calls("line_total").show()
#12 line_total(line={'sku': 'A1', 'quantity': 2, 'price': 5.0}) -> 10.0
#14 line_total(line={'sku': 'B2', 'quantity': 1, 'price': 12.5}) -> 12.5
#27 line_total(line={'sku': 'A1', 'quantity': 1, 'price': 5.0}) -> 5.0
#42 line_total(line={'sku': 'C3', 'quantity': 0, 'price': 7.0}) raised ValueError: 'bad quantity for C3'
```

Each call prints as `#index function(parameter=argument, …)` followed by its outcome. The index
is the call's position in the trace, and `t.call(index)` returns the call.

## Recording

### `pmdb-record`

[`skills/pmdb/scripts/pmdb-record`](../skills/pmdb/scripts/pmdb-record) runs a program and records
every call of its own functions, without modifying any file:

```
pmdb-record [-o TRACE] [--root DIR]... SCRIPT [ARGS...]
pmdb-record [-o TRACE] [--root DIR]... -m MODULE [ARGS...]     e.g. -m pytest -q tests/test_x.py::test_y
```

- **What is recorded.** Every call of a function or method defined in a `.py` file under the
  current directory, or under each `--root`. That includes test functions, nested functions,
  methods, generators and coroutines.
- **What is not recorded:**
  - code in installed packages (`site-packages`, `dist-packages`) and in the standard library;
  - lambdas, comprehensions and generator expressions;
  - class bodies and modules;
  - the recorder itself.
- **Running the program.** It runs as usual, with the same output and exit status. The trace is
  written when it exits, even if it raises. Options after the script or module go to the program.
- **Requirements.** It uses `sys.monitoring`, so Python 3.12 or later. The package `recorder`
  must be importable: put the directory `Python` of the pmdb repository on `PYTHONPATH`, unless
  the script runs from the repository.
- **Interpreter.** Run it with the interpreter that has the program's dependencies (e.g.
  `.venv/bin/python path/to/pmdb-record …`).

### From Python

```python
with recorder.recording("trace.pmdb"):                       # roots: the current directory
  run()
with recorder.recording("trace.pmdb", roots=["src"], exclude=["src/vendor"]):
  run()
```

`recording(path, roots=None, exclude=())` records the calls made while running the body. It
writes the trace when the body ends, even if it raises. For finer control, use
`recorder.Monitor(roots, exclude)` with `start()`, `stop()` and `write(path)`.

### Snaps

`recorder.snap(label, value)` records `value` in the call being run, under the string `label`.
It returns `value`, so it can wrap an expression:

```python
subtotal = recorder.snap("subtotal", sum(line_total(l) for l in self.lines))
```

It does nothing when no recording is active, so it can stay in code that runs unrecorded.

### How values are recorded

Values are encoded when they are observed: arguments when the call starts, results when it
returns, and snaps when taken. Later mutations don't change what was recorded.

| Python value | recorded as | loaded as |
|---|---|---|
| `None`, `True`, `False`, `int` (any size), `float`, `str` | itself | itself |
| `list`, `tuple` | array | `list` |
| `dict` with string keys, named tuple | table | `dict` |
| enum member | the string of its name | `str` |
| function | its qualified name | `Function` (a `str`) |
| object whose class defines `__pmdb__` or is `register`ed | the value that returns | that value, loaded |
| other object that can be pickled (class instances, sets, …) | its pickle | `Opaque` |
| other object | its `repr` | `str` |

- **Fields of your own classes.** To query them, give the class
  `def __pmdb__(self): return vars(self)` before recording, or call
  `recorder.register(cls, convert)` for a class you can't change. Its instances are then
  recorded as tables of their fields.
- **The value table.** A trace stores each value other than `None`, Booleans, numbers and
  strings shorter than 8 characters once, in a table of values. Equal values are compared by
  their encoding. Repeated arguments, such as a `self` that doesn't change or a configuration
  passed everywhere, cost one entry. This is invisible to queries.

## Selecting calls

```python
t.calls(*selectors, **conditions)            # every call of the trace that matches
calls.where(*selectors, **conditions)        # the calls of a selection that match
```

- **Result.** Both return a `Calls` selection, in the order the calls started.
- **Matching.** A call matches if it is selected by every selector and satisfies every
  condition.
- **No arguments.** `t.calls()` is every call.

### Selectors

| selector | selects |
|---|---|
| `"line_total"` | the calls of the function with that name, or whose qualified name ends with `.line_total` |
| `"Cart.total"` | the calls of the method `total` of `Cart` (a qualified name) |
| `re.compile(r"Cart\..*")` | the calls whose qualified name the regex matches in full |
| `lambda c: …` | the calls for which the predicate returns a true value |
| a `Call` | that call |
| a `Calls` or any collection of calls | those calls |
| `Q(*selectors, **conditions)` | the calls matching all of its selectors and conditions |

- **Names.** A function's name is its qualified name: `Cart.total`, `outer.<locals>.inner`. A
  name that matches no recorded function raises `QueryError`, so a typo can't silently select
  nothing.
- **Exact names.** To match one function among several with the same last component, use its
  qualified name or a regex.

```python
>>> t.calls(re.compile(r"Cart\..*")).functions()
{'Cart.add': 5, 'Cart.__init__': 3, 'Cart.total': 3}
```

### Conditions

| condition | holds for a call that |
|---|---|
| `where=pred` | satisfies `pred(call)` |
| `returned=True` / `returned=False` | returned / didn't return (raised, or didn't finish) |
| `returned=value` | returned a value equal to `value` |
| `returned=pred` | returned a value `r` such that `pred(r)` |
| `raised=True` / `raised=False` | raised / didn't raise |
| `raised="ValueError"` or `raised=ValueError` | raised an exception of that type (compared by the type's name) |
| `raised=pred` | raised an exception `e` (a `Raised`) such that `pred(e)` |
| `caller=sel` | was made directly by a selected call |
| `callee=sel` | made a selected call directly |
| `ancestor=sel` | was made during a selected call, directly or not |
| `descendant=sel` | made a selected call, directly or not |
| `before=sel` | started before a selected call started |
| `after=sel` | started after a selected call ended |

`sel` is any selector, including a single call. An unknown condition raises `TypeError` with the
list of conditions.

```python
>>> bad = t.calls("line_total", raised=True).one()
>>> t.calls("line_total", ancestor=Q("checkout", where=lambda c: c["code"] == "SAVE10")).values("line")
[{'sku': 'A1', 'quantity': 2, 'price': 5.0}, {'sku': 'B2', 'quantity': 1, 'price': 12.5}]
>>> t.calls("checkout", descendant=Q("line_total", raised=True))
Calls([#38 checkout(cart=<Cart>, code='SAVE20') -> None])
>>> t.calls("Cart.total", caller="checkout", returned=lambda r: r > 10)
Calls([#11 Cart.total(self=<Cart>, discount=0.1) -> 20.25])
>>> t.calls("discount_for", returned=0).values("code")
[None]
>>> t.calls("line_total", before=bad).count(), t.calls("line_total", after=bad).count()
(3, 0)
```

### Combining with `Q`

`Q(*selectors, **conditions)` is a selection that can be named, reused, nested in conditions, and
combined:
- `q1 & q2` matches calls matching both;
- `q1 | q2` matches calls matching either;
- `~q` matches calls not matching `q`.

```python
>>> big_order = Q("checkout", where=lambda c: len(c["cart"].unpickle().lines) > 1)
>>> t.calls(big_order).values("code")
['SAVE10', 'SAVE20']
>>> t.calls(Q("Cart.add") | Q("Cart.__init__")).count()
8
>>> t.calls(~Q(ancestor="checkout")).functions()
{'Cart.add': 5, 'Cart.__init__': 3, 'checkout': 3, 'main': 1}
```

**Negate the condition, not the selector inside it.**
- `~Q(ancestor="checkout")` is "not made during any checkout".
- `ancestor=~Q("checkout")` is "made during some call that isn't a checkout", such as `main`.
  That holds for nearly every call.

## Selections

A `Calls` is a `list` of calls in the order they started. Slices are selections too.

| method | returns |
|---|---|
| `where(*selectors, **conditions)` | the calls that match (see above) |
| `first()`, `last()` | the first or last call, or `None` if the selection is empty |
| `one()` | the only call; raises `QueryError` if there are none or several |
| `count()` | the number of calls (`count(x)` counts occurrences of `x`, as for lists) |
| `values(key)` | the value of `key` for each call |
| `group_by(key)` | a `dict` from each value of `key` to the selection of calls having it, in order of first appearance |
| `count_by(key)` | a `collections.Counter` from each value of `key` to its number of calls |
| `functions()` | a `dict` from each function to its number of calls, most frequent first |
| `show(limit=20)` | prints the first `limit` calls, one per line |
| `a \| b`, `a & b`, `a - b` | the union, intersection or difference of two selections, in recording order |

- **Keys.** A key is a parameter name (`"code"`), a position (`0`) or a function on calls
  (`lambda c: c["line"]["sku"]`).
- **Grouping on containers.** Lists and dicts in a key's value are turned into tuples, so they
  can be grouped and counted.

```python
>>> t.calls("line_total").count_by(lambda c: c["line"]["sku"])
Counter({'A1': 2, 'B2': 1, 'C3': 1})
>>> {code: len(calls) for code, calls in t.calls("checkout").group_by("code").items()}
{'SAVE10': 1, None: 1, 'SAVE20': 1}
>>> len(t.calls("line_total") - t.calls("line_total", ancestor=Q("checkout", where=lambda c: c["code"] is None)))
3
```

## Calls

### Arguments

| attribute | value |
|---|---|
| `c["name"]` | the argument of the parameter `name`; raises `KeyError` naming the call's parameters if there's none |
| `c[i]` | the `i`-th positional argument |
| `c.get("name", default=None)` | the argument of `name`, or `default` |
| `c.params` | a `dict` from each parameter to its argument |
| `c.args` | the positional arguments, a method's `self` first |
| `c.kwargs` | the arguments of keyword-only parameters and `**` |
| `c.names` | the parameter of each positional argument |

- **Bound arguments.** Arguments are recorded as Python bound them, with defaults included.
- **Variadic parameters.**
  - The arguments collected by `*rest` are positional, named `*rest` in `names`, and a list
    named `rest` in `params`.
  - Those collected by `**options` are named arguments of their own.

```python
>>> total = t.calls("Cart.total").first()
>>> total.params
{'self': <shop.Cart object; .unpickle() rebuilds it>, 'discount': 0.1}
>>> total.args, total.kwargs, total.names
([<shop.Cart object; .unpickle() rebuilds it>, 0.1], {}, ['self', 'discount'])
```

### Outcome

| attribute | value |
|---|---|
| `c.returned` | `True` if the call returned |
| `c.raised` | `True` if the call raised |
| `c.result` | the value it returned, or `None` |
| `c.exception` | the exception it raised, a `Raised` with `type` and `message`, or `None` |

`c.returned` is a Boolean. To compare the value a call returned, use `c.result` or the condition
`returned=value`. `c.returned == "x"` is always false.

```python
>>> bad.exception, bad.exception.type, bad.exception.message
(ValueError('bad quantity for C3'), 'ValueError', 'bad quantity for C3')
```

A call that neither returned nor raised hadn't finished when the trace was written: the program
exited during it, or it was a generator that was never exhausted.

### Function and location

| attribute | value |
|---|---|
| `c.function` | the qualified name of the function, e.g. `Cart.total` |
| `c.name` | its last component, e.g. `total` |
| `c.location` | `(file, line)` of the call site |
| `c.definition` | `(file, line)` of the function's definition |
| `c.end_location` | `(file, line)` where the call returned or raised |
| `c.index` | the call's position in the trace (`#index` when printed); `t.call(index)` returns it |

### Relations

| method | returns |
|---|---|
| `c.caller` | the call that made it, or `None` for a call made at the top level |
| `c.callees(*selectors, **conditions)` | the calls it made directly |
| `c.ancestors(*selectors, **conditions)` | the calls it was made during, innermost first |
| `c.ancestor(*selectors, **conditions)` | the innermost of those that match, or `None` |
| `c.descendants(*selectors, **conditions)` | the calls made during it, directly or not, in recording order |
| `c.path()` | the calls from the outermost one down to `c` |
| `c.tree(depth=3, limit=50)` | prints `c` and the calls made during it, as a tree |

The methods taking selectors and conditions return only the calls that match them.

```python
>>> [c.function for c in bad.path()]
['main', 'checkout', 'Cart.total', 'line_total']
>>> bad.ancestor("checkout")["code"]
'SAVE20'
>>> total.callees()
Calls([#12 line_total(line={'sku': 'A1', 'quantity': 2, 'price': 5.0}) -> 10.0, #14 line_total(line={'sku': 'B2', 'quantity': 1, 'price': 12.5}) -> 12.5])
>>> t.roots()[0].tree(depth=2)
#1 main() -> None
  #2 Cart.__init__(self=<Cart>, customer='ana') -> None
  #4 Cart.add(self=<Cart>, line={'sku': 'A1', 'quantity': 2, 'price': 5.0}) -> None
  #6 Cart.add(self=<Cart>, line={'sku': 'B2', 'quantity': 1, 'price': 12.5}) -> None
  #8 checkout(cart=<Cart>, code='SAVE10') -> 20.25
    #9 discount_for(code='SAVE10') -> 0.1
    #11 Cart.total(self=<Cart>, discount=0.1) -> 20.25
      … 2 calls
  …
```

## Snaps

| expression | returns |
|---|---|
| `t.snaps(label=None)` | the snaps with `label` (a string, or a compiled regex matching the whole label), or all of them |
| `c.snaps(label=None, deep=False)` | the snaps taken directly during `c` (with `deep=True`, also during the calls it made) |

A selection of snaps (`Snaps`) has `labeled(label)`, `where(pred)`, `values()`, `first()`,
`last()` and `show(limit)`. A snap has `label`, `value`, `location`, `index`, and `call`, the call
it was taken during.

```python
>>> t.snaps("subtotal").values()
[22.5, 5.0]
>>> t.snaps("subtotal")[0].call
#11 Cart.total(self=<Cart>, discount=0.1) -> 20.25
>>> total.snaps("subtotal").values()
[22.5]
```

The third cart has no `subtotal` snap, because `line_total` raised before `snap` ran.

## Values

Values load as Python values, following the table under
[How values are recorded](#how-values-are-recorded):
- named tuples are dicts, so `c["line"]["sku"]`, not `c["line"].sku`;
- tuples are lists;
- objects are `Opaque`.

- **Separate copies.** Each call decodes its own copy of its values, the first time they are
  read. Changing a value you read changes neither the trace nor other calls' values.
- **`Opaque`:**
  - It prints as `<module.Class object; .unpickle() rebuilds it>`, or as `<Class>` inside a call.
  - `type` is the class's qualified name.
  - `unpickle()` rebuilds the object. That imports the program's modules, which must be
    importable (e.g. with the program's directory on `sys.path`), and runs their code: unpickle
    objects of trusted programs only.
  - Classes defined in a script run as `__main__` can't be unpickled from another script.
- **`Raised`** is a dict with the properties `type`, the exception's class name, and `message`,
  its `str`.
- **`Function`** is a `str` holding a function's qualified name.

```python
>>> total["self"].type
'shop.Cart'
>>> total["self"].unpickle().lines
[Line(sku='A1', quantity=2, price=5.0), Line(sku='B2', quantity=1, price=12.5)]
```

## Errors

Queries fail loudly rather than silently selecting the wrong calls (tracebacks shortened):

```python
>>> t.calls("checkout", where=lambda c: c["coupon"])
QueryError: the where predicate raised KeyError: "'coupon': checkout has parameters cart, code" on #8 checkout(cart=<Cart>, code='SAVE10') -> 20.25; make it handle that case (e.g. `c.get("name")`, or a test for `None`)
>>> t.calls("chekout")
QueryError: no recorded function is named 'chekout'; see `functions()`
>>> t.calls("checkout", parent="main")
TypeError: unknown condition parent=; the conditions are where, returned, raised, caller, callee, ancestor, descendant, before, after
>>> total.return_value
AttributeError: Call has no attribute 'return_value'; did you mean returned?
>>> t.calls("checkout").one()
QueryError: expected one call, found 3
```

- **Failing predicates.** A predicate that raises on some call stops the query with a
  `QueryError` naming that call. Make the predicate handle the case, with `c.get(…)` or a test
  for `None`, rather than leaving such calls out silently.
- **Grouping keys.** The same holds for `values`, `group_by` and `count_by` keys.

## What to keep in mind

- **Order.**
  - Calls are in the order they started, and `#index` reflects it.
  - `before=` compares the starts of calls.
  - `after=` compares a call's start with the end of the selected call. A generator's or
    coroutine's call ends when it finishes, not when it yields.
- **Generators and coroutines** are one call each, from when they first run to when they finish.
  - The value they return (`return x` in a generator) is their result.
  - Calls made while they run are nested in them.
  - Calls made by their consumer while they are suspended are not.
- **Exceptions propagate.** An exception is recorded on every recorded call it passes through. In
  the example, both `line_total` and `Cart.total` raised. `checkout` caught it, so it returned.
  The calls where exceptions started are those that raised without a callee that raised:
  `t.calls(Q(raised=True) & ~Q(callee=Q(raised=True)))`. Note that
  `callee=~Q(raised=True)` would mean "made some call that didn't raise".
- **Arguments are recorded when the call starts.** A list the call mutates shows its old contents
  in the call's arguments; the new contents appear in later calls' arguments, or in a snap.
- **Threads.** Each thread's calls form their own branch: `t.roots()` has one top-level call per
  thread and per top-level call.
- **Scanning cost.** Each `t.calls(…)` scans the whole trace, and each relation condition is
  computed once per query. Inside a loop over calls, use `c.callees(…)`, `c.descendants(…)` and
  `c.ancestors(…)`, which only look at the calls around `c`.
- **Load once.** Load the trace once per script. Loading takes about 10 seconds for a trace of a
  million calls; values are decoded only when they are read.
- **Other recorders.** Traces written by the `Recorder` decorator, by the Rust recorder, or by
  older versions of the recorder load too.
  - Their calls have no parameter names, so only `c.args`, `c.kwargs` and `c[i]` are available
    for positional arguments.
  - `c.definition` is `None`.

## Reference

Exported by `recorder`:
- **`load(path)`**: the `Trace` at `path`.
- **`Q(*selectors, **conditions)`**: a reusable selection.
- **`Calls`**: a selection of calls.
- **`QueryError`**: raised by failing queries.
- **Recording:** `recording(path, roots=None, exclude=())`, `snap(label, value)`, `Monitor`,
  `register(cls, convert)`.

**`Trace`**
- `calls(*selectors, **conditions)`, `call(index)`;
- `roots()`;
- `snaps(label=None)`;
- `functions()`.

**`Calls(list)`**
- `where(*selectors, **conditions)`;
- `first()`, `last()`, `one()`, `count()`;
- `values(key)`, `group_by(key)`, `count_by(key)`;
- `functions()`, `show(limit=20)`;
- `|`, `&`, `-`.

**`Call`**
- arguments: `c[key]`, `get(key, default=None)`, `params`, `args`, `kwargs`, `names`;
- outcome: `returned`, `raised`, `result`, `exception`;
- function and location: `function`, `name`, `location`, `definition`, `end_location`, `index`;
- relations: `caller`, `callees(…)`, `ancestors(…)`, `ancestor(…)`, `descendants(…)`, `path()`;
- snaps and printing: `snaps(label=None, deep=False)`, `tree(depth=3, limit=50)`,
  `describe(width=160)`.

**`Snap`** has `label`, `value`, `location`, `index` and `call`. **`Snaps(list)`** has
`labeled(label)`, `where(pred)`, `values()`, `first()`, `last()` and `show(limit=20)`.

**Values:**
- `Opaque`, with `type`, `unpickle()`, `pickled` and `description`;
- `Raised(dict)`, with `type` and `message`;
- `Function(str)`.
