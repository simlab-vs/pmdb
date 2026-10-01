# pmdb usability findings: what agents tried, why it failed, and what to change

This document goes into detail on round 1 of the [usability study](REPORT.md). It covers every
pmdb command the agents ran (42 commands in 9 runs, all by Haiku; Sonnet read the README in all
10 of its runs and never ran pmdb). For each problem, it records:

- **what agents tried**, quoted from the transcripts ([pmdb_attempts.md](pmdb_attempts.md) lists
  all of them);
- **its cause**, one of:
  - *Promised but broken*: the documentation says it works, and it doesn't;
  - *Documentation unclear*: the behavior is defensible, but the documentation misled, said
    nothing, or contradicted itself;
  - *Not supported (documented)*: the documentation is clear, but agents reached for it first,
    which makes it a candidate feature;
  - *Output or error problem*: the command did something, but its output or error message misled;
- **the current behavior**, re-run on `ci` in the agents' sandbox on their traces
  ([pmdb_reproduced.md](pmdb_reproduced.md) has the full outputs). pmdb's sources have not changed
  since the frozen study version `a9cb57d`, so this is what any agent would see today.
- **what to change**.

About the documentation: agents got `/opt/pmdb/README.md`. Its first 40 lines are a header
written for the study ([opt-pmdb/HEADER.md](../opt-pmdb/HEADER.md)), covering recording,
observations and commands. The rest is the repository README's "Query Language" section,
verbatim. Each quote below says which part it comes from.

## Summary

| # | Problem | Commands affected | Cause | Priority |
|---|---|---|---|---|
| 1 | Selecting a call's return value | 7 (1 silently empty) | Documentation unclear, plus a missing feature and a misleading error | **highest** |
| 2 | Matching arguments by value | 5 (1 silently empty) | Not supported (documented), but the agents' first instinct | high |
| 3 | Writing where clauses | 5 | Documentation unclear (string quotes, `_`), missing feature (key test), misleading error (`and`) | high |
| 4 | `from` clauses | 3 | Documentation unclear (`<source>` never defined, semantics vague) | medium |
| 5 | Running several commands | 5 | Documentation unclear (variables per invocation), output problem (REPL prompts) | medium |
| 6 | Command-line usage | 4 | Output problem (`--show` is an option with a value; usage says "driver") | low |
| 7 | Output volume and `<object>` | 9 `--show` commands cut with `head`/`grep` | Missing feature (filtering, objects) | medium |
| 8 | First impression of the README | 19 reads; Sonnet never ran pmdb | Documentation (no task-shaped examples) | high |

**No failure was a feature the documentation promises and pmdb doesn't deliver.** Everything
the README describes behaved as described when used as described. The closest case is table
properties (section 3): `o.coupon` works, but the documented rule that one failing observation
fails the whole query makes it unusable for optional keys. The failures come from three sources:
- documentation that leaves the agent's natural reading open (return values, string quotes,
  `from`, variables);
- missing features that agents expect from Python habits (values in patterns, `and`);
- error messages that point the wrong way. Most of them, "multiple commands should be separated
  by a newline" above all, appear when the parser stops early and blames the leftover text.

What worked (the forms to make prominent): `select f(...)`, `select f(*)`, `select f(_, _, _)`,
`select f(a, b) where b == "x" && …` (double-quoted strings, names bound in the pattern), and
`select /f\.\$result/` (single-quoted in the shell). When a query worked, it showed the cause
directly in ex04 and ex07.

---

## 1. Selecting a call's return value

**What agents tried.** Every Haiku run that used pmdb wanted a call's result.

| Command | Run | Result |
|---|---|---|
| `select merge(_).$result` | pilot | `error: multiple commands should be separated by a newline` |
| same, in the REPL via a heredoc | pilot | the same error, then `undefined symbol '$0'` |
| `select spread(*)` + `show $0`, then grep for `result` | ex02 | nothing: `show` prints calls without results |
| `select /utilization/\.\$result/` | ex05 | `error: multiple commands should be separated by a newline` |
| `select /fastest_route/.*result/` | ex08 (×2) | the same error |
| `select /fastest_route.*\$result/ where true` in shell double quotes | ex07 | `$0 = <0 element(s) …>`: silently empty |
| `select /spread\.\$result/` | ex02 | worked |

**Cause.**
- *Documentation unclear.*
  - The header says: "Each call is followed by a snap labeled `<function>.$result` holding its
    return value."
  - The README says a snap pattern "can be a simple identifier, a regular expression, or a
    wildcard", with one example, `/.*\$result/`.

  Nothing says the documented label (`merge.$result`) is *not* a valid pattern because it
  contains `.` and `$`, or that the result is a separate observation next to the call, not part
  of it.
- *Missing feature.* There is no way to get a call together with its result: listings and
  `show` print only the call, and a call pattern can't bind the result.
- *Output problem.*
  - `merge.$result` and `merge(_).$result` fail with a message about separating commands. The
    parser stops after `merge(_)` and treats the rest as a second command.
  - The `$` in labels clashes twice:
    - with shell double quotes: `"\$result"` reaches pmdb as `$result`;
    - with the regex end anchor: `/f.*$result/` can never match.

    Both give an empty result instead of an error.

**Current behavior.**
```
$ pmdb report.pmdb -e 'select merge.$result'
error: multiple commands should be separated by a newline
$ pmdb report.pmdb -e "select /fastest_route.*\$result/"
$0 = <0 element(s) in 0 trace(s)>
$ pmdb report.pmdb -e 'select /fastest_route.*\$result/'
$0 = <6 element(s) in 1 trace(s)>
/work/main.py:15: snap fastest_route.$result = [332, [E0, Avenue E, E1, …]]
```

**What to change.**
1. Show results with calls everywhere, e.g. `call spread(5000, [40, 12]) → [1, 0]` in `select`
   listings and `show`. This alone removes most of the need to select results.
2. Let call patterns bind the result: `select spread(amount, ws) -> r where r[0] == 0`, or a
   predefined `result` name in where clauses.
3. Accept the documented label as a pattern: `select merge.$result` (and quoted labels in
   general).
4. Give a specific error for `f(…).x` or `f.x`: "to select results use `f(...) -> r` or
   `/f\.\$result/`".
5. Warn when a regex contains `$` followed by more characters (it can never match), and mention
   the shell quoting trap in the docs. Alternatively, rename the labels so they don't use `$`
   (e.g. `merge→`), keeping the old ones as aliases.

## 2. Matching arguments by value

**What agents tried.**

| Command | Run | Result |
|---|---|---|
| `select spread(5000, [3597610, 33068])` | ex02 | `error: expected identifier` |
| `select fastest_route(E0, A0)` | ex07 | `$0 = <0 element(s) …>`: silently empty |
| `select call('parse', _) where _ > 0` | ex04 | `error: expected identifier` |
| `select fastest_route($0)` | ex07 | `error: expected identifier` |
| `select utilization($) where _ != none` | ex05 | `error: expected identifier` |

**Cause.** *Not supported (documented).* The README says it plainly: "A positional pattern can be
either a wildcard (i.e., `_`) or a variable". Values must be compared in a where clause. But
agents' first instinct is to write values in the pattern, as in Python call syntax.
`fastest_route(E0, A0)` is the dangerous case. It is valid: it binds two *variables* `E0` and
`A0`, and matches nothing because the function takes three arguments. Nothing tells the agent
that.

**Current behavior.**
```
$ pmdb report.pmdb -e 'select fastest_route(E0, A0)'
$0 = <0 element(s) in 0 trace(s)>
$ pmdb report.pmdb -e 'select fastest_route(_, E0, A0)'      # E0, A0 bind any values
$0 = <6 element(s) in 1 trace(s)>
/work/main.py:15: call fastest_route(<object>, F3, E0)
…
$ pmdb report.pmdb -e 'select fastest_route(n, s, t) where s == "B2" && t == "A0"'
$0 = <1 element(s) in 1 trace(s)>
```

**What to change.**
1. Allow literal patterns: numbers, double-quoted strings, `none` and arrays, as in
   `spread(5000, _)` or `fastest_route(_, "E0", "A0")`.
2. When a query matches nothing but the function exists, say why: "`fastest_route` was called 6
   times, always with 3 positional arguments; the pattern has 2".
3. Make the "expected identifier" error list what is allowed in an argument pattern (`_`, a
   name, `x*`, `x**`, `name = pattern`, `...`) and point to where clauses for values.

## 3. Writing where clauses

**What agents tried.**

| Command | Run | Result |
|---|---|---|
| `… where code == 'BIG50'` | ex01 (×2) | `error: expected expression` (single quotes) |
| `… where source == 'B2' and target == 'A0'` | ex08 | `error: expected expression`; with double quotes, `error: multiple commands should be separated by a newline` (`and`) |
| `select subtract(_, _) where _` | ex06 | `error: expected expression` |
| `select utilization(_) where _ != none` | ex05 | `error: expected expression` |
| `select coupon_reductions(...) where code == "BIG50"` (reproduced) | — | `error: undefined symbol 'code'`: a clear error |
| `select invoice(o) where o.coupon == "BIG50"` (reproduced) | — | `error: undefined property 'coupon'` |

**Cause.**
- *Documentation unclear.*
  - The grammar lists `string-literal` but never says strings use double quotes only.
  - The README calls `_` a wildcard but doesn't say it can't be used in an expression.
  - The operator list does give `&&` and `||`, so `and` is a guess carried over from Python.
- *Missing feature.* Table properties work, but most orders have no `coupon` key, and "if the
  evaluation of a where clause fails for any of the matching observations … the query fails"
  (documented). There is no way to test whether a key exists, so "orders whose coupon is BIG50"
  cannot be expressed at all.
- *Output problem.* `and` produces the separate-commands error instead of "unknown operator
  `and`; use `&&`", and no error shows a position.

**Current behavior.** The same as the table. `o.id == "0-4"` works because every order has an
`id`.

**What to change.**
1. Accept single-quoted strings, or reject them with "strings use double quotes".
2. Accept `and`, `or` and `not` as aliases, or reject them with a suggestion.
3. Give missing table keys a way to be tested: either `o.coupon` evaluates to `none` when the
   key is missing, or add `o.has("coupon")` / `o.get("coupon")`.
4. Give `_` in an expression its own error: "`_` matches without binding; give the argument a
   name to use it in `where`".
5. Show the column and the source text with a caret in every parse error.

## 4. `from` clauses

**What agents tried.**

| Command | Run | Result |
|---|---|---|
| `select spread(*) from * where true` | ex02 | `error: expected 'select'` |
| `select /coupon_reductions.*\$result/ from coupon_reductions(...)` | ex01 | `error: expected 'select'` |
| `select coupon_reductions(...) from coupon_reductions(...)` | ex01 | the same (hidden by `grep`) |
| `… from select coupon_reductions(...)` (reproduced) | — | `$0 = <0 element(s) …>` |
| `select invoice(o) where o.id == "0-4"` then `select line_subtotal(l) from $0` (reproduced) | — | `$1 = <0 element(s) …>` |

**Cause.** *Documentation unclear.*
- The README gives the form `<pattern> [from <source>] [where <expression>]` but never defines
  `<source>`. Only the parser tells you it must be a variable (`$0`) or a nested `select`.
- The meaning is vague too: "specifies the set of observations in which the query will be
  executed". In fact `from $0` searches only the observations *in* `$0`. It doesn't search the
  calls made inside them, or their `$result` snaps, which sit next to the call.
- Agents (and the README's wording) expected scoping into a call, e.g. "the results of the
  `coupon_reductions` call that handles BIG50", which is not possible today.

**What to change.**
1. Document `<source> ::= $N | select <query>` with one example each.
2. Add scoping into the call tree: `select line_subtotal(l) in $0`, meaning observations inside
   the calls of `$0`, and possibly `after`/`next` for the snap that follows a call.
3. When `from` receives something else, say what is allowed: "expected a variable (`$0`) or a
   nested `select` after `from`".

## 5. Running several commands

**What agents tried.**

| Command | Run | Result |
|---|---|---|
| `pmdb report.pmdb -e 'show $0'` (new invocation) | ex10 | `error: undefined symbol '$0'` |
| `echo "select spread(...) \| show \$0" \| pmdb report.pmdb` | ex02 (×2) | `error: expected identifier` / `expected 'select'`, plus `(pmdb) (pmdb)` prompts |
| heredoc into the REPL | pilot, ex08 | after a failed `select`, the next line fails with `undefined symbol '$0'` |
| `printf 'select merge(_)\nshow $0\n' \| pmdb report.pmdb` (reproduced) | — | works, but every line starts with `(pmdb) ` |

**Cause.**
- *Documentation unclear.* Nothing says variables live only for one invocation. The header says
  `select` "assigns its result to the next variable `$0`", which reads as persistent.
- *Not supported.* `|` between commands; the README says nothing about separators.
- *Output problem.*
  - Piped input still prints `(pmdb) ` prompts and the `continue?` question.
  - In the REPL, a failed `select` doesn't define `$0`, so every later command fails too.

**What to change.**
1. Allow `;` between commands in one `-e`, and reject `|` with "use `;` or another `-e`".
2. Make the undefined-variable error explain itself: "`$0` is undefined: variables only exist
   within one pmdb invocation; run the `select` in the same command".
3. Without a terminal on stdin, print no prompts and no `continue?`.
4. Optional, for agents: a session file (`pmdb --session s.json`) that keeps variables across
   invocations.

## 6. Command-line usage

**What agents tried.** `pmdb /work/report.pmdb --show | head` (ex02, ex07, ex04 ×2).

**Cause.** *Output problem.*
- The header shows the right form (`pmdb --show trace.pmdb`), but `--show` is an *option that
  takes the file*, so putting it after the trace fails.
- The error and help name the program `driver`.

**Current behavior.**
```
$ pmdb report.pmdb --show
Error: Missing value for '--show <show>'
Usage: driver [--show <show>] [--export-xml <export-xml>] [<inputs> ...] [--execute <execute> ...]
```

**What to change.**
1. Make `--show` a flag that applies to the positional trace(s), so both orders work.
2. Set the command name to `pmdb` (`CommandConfiguration(commandName: "pmdb")`).

## 7. Output volume and `<object>`

**What agents did.** When queries failed, agents fell back to `pmdb --show` (200–380 lines for
these small programs, more for calc) and to `show $0` for many calls (30 `subtract` calls gave
211 lines). They cut the output with `head`/`grep` and sometimes cut off the part they needed.
Instances of the programs' classes (`Network`, `Parser`, `Closure`) appear as `<object>`.

**Cause.**
- *Missing feature.* There is no filtering or depth limit for `--show`, no way to `show`
  without source excerpts, and no summary of repeated calls.
- *Objects.* Since `3590cc2`, a class can opt in through `__pmdb__` or `recorder.register`. By
  default, instances are still `<object>`, and agents didn't know about the opt-in, which is not
  in the README section they saw.

**What to change.**
1. `--show` options: `--function f`, `--depth N`, `--results` (results only), and collapsing of
   repeated identical calls.
2. `show $N --no-source`, or a `list $N` command.
3. Record the attributes of plain objects (`vars(o)`) as a table by default, keeping `<object>`
   for objects that have none or can't be recorded.

## 8. First impression of the README

**What agents did.**
- Sonnet read the README in every run (about 175 lines, roughly 10k tokens) and then never ran
  pmdb. Its feedback: *"the query language … looked non-trivial to construct correctly on the
  first try … compared to just reading the ~130-line source file directly"*.
- Haiku read it and then guessed at syntax (sections 1–5).
- One agent took the "under development" note as a reason to distrust the tool.
- Several agents believed features were missing that exist. For example, *"No way to filter
  results by argument values"*: where clauses do exactly that.

**Cause.** *Documentation.* The README is a grammar reference. The few examples
(`f(x) where x > 1`, `f(xs*) where xs.all(…)`) don't match what debugging needs: results, value
filters, and calls inside a call.

**What to change.** Start the README with a short "debugging recipes" section that a reader can
copy directly, with the output of each:

| To | Write |
|---|---|
| list calls of `f` with their results | `select f(...)` (once results are shown with calls) |
| find calls where an argument has a value | `select f(a, b) where b == "x"` |
| find calls that returned a value | `select /f\.\$result/` … (or `f(...) -> r where r == 0`) |
| look inside one call | `select g(...) in $0` (proposed) |
| several commands in one go | `pmdb t.pmdb -e 'select …' -e 'show $0'` |
| the whole tree | `pmdb --show t.pmdb` |

Put the grammar after the recipes, define every placeholder (`<source>`, string literals), and
drop or soften "under development".

---

## Suggested order of work

1. Show results next to calls (1.1) and the recipes section (8). These address most failed
   attempts and the reason Sonnet didn't use pmdb.
2. Errors with a position and a suggestion (1.4, 2.3, 3.4, 3.5, 4.3, 5.2). Cheap, and every
   failed command would have pointed to the fix.
3. Literal argument patterns and arity hints (2.1, 2.2).
4. Single quotes, `and`/`or`, missing keys (3.1–3.3).
5. `;` separators and no prompts without a terminal (5.1, 5.3); the `--show` flag and the
   command name (6).
6. `in` scoping (4.2), `--show` filtering (7.1), default object attributes (7.3).

Each change can be checked by re-running round 1's exercises: the same failing commands from
[pmdb_attempts.md](pmdb_attempts.md) should now succeed, or fail with an error that names the
fix.
