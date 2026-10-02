# pmdb usability findings, round 2: what agents tried, why it failed, and what to change

This document goes into detail on round 2 of the [usability study](REPORT.md). It covers every
pmdb command the agents ran outside the pilot: 44 commands in 12 runs. Haiku ran 41 of them, in
all 10 of its pmdb-arm runs; Sonnet ran 3, in 2 runs, and debugged the other 8 by reading. For
each problem, it records:

- **what agents tried**, quoted from the transcripts ([pmdb_attempts.md](pmdb_attempts.md) lists
  all of them);
- **its cause**, one of round 1's categories:
  - *Promised but broken*: the documentation says it works, and it doesn't;
  - *Documentation unclear*: the behavior is defensible, but the documentation misled, said
    nothing, or contradicted itself;
  - *Documented, ignored*: the skill describes the behavior, and the agent had read it (new in
    this round);
  - *Not supported*: the documentation is clear, but agents reached for it first, which makes it a
    candidate feature;
  - *Output or error problem*: the command did something, but its output or error message misled;
- **the current behavior**, re-run with the study's pmdb in the agents' sandboxes on their traces
  ([pmdb_reproduced.md](pmdb_reproduced.md) has the full outputs). pmdb hasn't changed since the
  frozen study version `7a1d6e7`, so this is what any agent would see today;
- **what to change**.

About the documentation: agents got the skill [`skills/pmdb`](../../../../skills/pmdb/SKILL.md)
as a Claude Code skill, and no README. Haiku invoked it in all 10 of its runs, always before its
first pmdb command; Sonnet in 2 of 10. Quotes below are from `SKILL.md` at `7a1d6e7`.

## Summary

| # | Problem | Commands affected | Cause | Priority |
|---|---|---|---|---|
| 1 | Referring to results with `show` | 7 failed | Documented, ignored; error messages that don't say what's expected | **highest** |
| 2 | `*` before other positional patterns matches nothing | 1, silently empty | **Promised but broken** | **high** |
| 3 | Bare names in patterns | 2, silently 19× too many matches (78 KB of output each) | Documented, ignored; silent | high |
| 4 | Queries in other languages' syntax | 3 failed | Not supported (SQL `from … like`, a `raised` keyword) | medium |
| 5 | A regex for one function's exception | 1 failed | Documentation unclear | low |
| 6 | Comparing values of different types | 1 failed | Documented; semantics worth revisiting | medium |
| 7 | Output volume | 2 outputs of 78 KB, 1 of 46 KB, 9 `--show` cut with `head`/`grep` | Output problem; skill recipes unused | high |
| 8 | Empty results that look like broken queries | 1 run gave up on queries | Output problem | medium |
| 9 | Sonnet doesn't use pmdb | 8 of 10 runs | Exercises easy to read | (see round 3) |

**One failure is a promised feature that doesn't work** (section 2): the README says a variadic
positional pattern "matches any number of positional arguments", but it consumes all remaining
ones, so a positional pattern after it never matches. Everything else behaved as documented.

**The skill removed round 1's main problems.** No command failed on return values, matching by
value, the command line or string quotes, which caused most of round 1's failures (see "Round 1's
problems, revisited"). The remaining failures are mostly forms the skill warns against and that
Haiku used right after reading it. That points at error messages and silent results rather than
at more documentation.

What worked (forms to keep prominent):
- `select f(...)` then `show $0`, with results next to calls: the key step in ex01, ex06, ex09 and
  ex10;
- binding and filtering: `select coupon_reductions(lines, subtotals, code) where code == "BIG50"`,
  `select invoice(o) where o.id == "0-4"`;
- literal and result patterns: `select fastest_route(_, "E0", "A0") -> r`, `select evaluate(...) -> -4`,
  `select turn_penalty(...) -> p where p == 26`;
- exceptions: `select /.*\$exception/` then `show $0`.

---

## 1. Referring to results with `show`

**What agents tried.**

| Command | Runs | Result |
|---|---|---|
| `select spread(...)` then `show query` | ex01 (×3) | `error: expected variable` |
| `select evaluate(*, _, *) -> r where r == 60` then `show --query` | ex03 | `error: expected variable` |
| `select spread(*, *)` then `show $1` | ex02 | `error: undefined symbol '$1'` |
| `select describe(path) where path.len() != 7` then `show $1` | ex07 | the same |
| `select evaluate(...) -> -4` then `show $1` | ex04 | the same |

Each agent fixed the variable on its next try, except in ex01 and ex03, where Haiku gave up on
queries and switched to `pmdb --show | grep`.

**Cause.**
- *Documented, ignored.* The skill says: "`select <query>` prints `$N = <k element(s) in 1
  trace(s)>` and stores the matches in `$N` (`$0`, `$1`, … in the order of the `select`s)", and
  every example is `show $0`. The `$1` errors come from numbering variables from 1, or counting
  the `show` as a command that creates a variable.
- *Error problem.* `expected variable` doesn't say what a variable looks like, and `undefined
  symbol '$1'` doesn't say which variables exist. pmdb has just printed `$0 = …` on the line
  above, but agents don't connect the two.

**Current behavior.** As above (pmdb_reproduced.md, "show $1 after one select", "show query",
"show --query").

**What to change.**
- **Name what's expected in the parse error**, without guessing intent:
  `error: show expects a variable, such as $0`.
- **List the defined variables in the undefined-variable error**:
  `error: undefined variable '$1'; defined: $0`.
- Both are plain facts about the grammar and the session, not heuristics about what the agent
  meant.

## 2. `*` before other positional patterns matches nothing

**What agents tried.** In ex03, `select evaluate(*, _, *) -> r where r == 60` returned
`$0 = <0 element(s) in 0 trace(s)>`. `evaluate(tree, environment=None, depth=0)` is called
7,685 times with three positional arguments. The agent concluded the query language couldn't
express what it wanted and used `--show | head` instead.

**Cause.** *Promised but broken.* The README says "A variadic positional pattern (`*`) matches any
number of positional arguments", and its definition of matching ("each argument of the call is
matched by a different argument pattern and every argument pattern is matched, with positional
patterns matching positional arguments in order") allows `*, _, *`. But `ArgumentPatternList`
lets `*` consume every remaining positional argument, so a positional pattern after it always
fails.

**Current behavior.** In ex03's trace:

| Pattern | Matches | Expected |
|---|---|---|
| `evaluate(_, *)` | 7,685 | 7,685 |
| `evaluate(_, _, *)` | 7,678 | 7,678 |
| `evaluate(*, _)` | 0 | 7,685 |
| `evaluate(_, *, _)` | 0 | 7,678 |
| `evaluate(*, _, *)` | 0 | 7,685 |

**What to change.** Match `*` against any number of positional arguments, as documented, by
trying each split (patterns are short, so backtracking is cheap). Alternatively, reject patterns
with a positional pattern after `*` at parse time. Either way, not silently.

## 3. Bare names in patterns

**What agents tried.** In ex08, Haiku wanted the penalty of turning from south to west:

| Command | Result |
|---|---|
| `select turn_penalty(...) -> p` then `show $0` | 78.5 KB, saved to a file by Claude Code |
| `select turn_penalty(S, W) -> p` then `show $0` | the same 78.5 KB: 227 matches |
| `select turn_penalty(...) -> p where p == 26` then `show $0` | 51 matches, 307 lines; useful |

`turn_penalty("S", "W")` matches 12 calls.

**Cause.**
- *Documented, ignored.* The skill's pitfalls say: "**Bare names in patterns are variables.**
  `f(E0)` matches any argument; write `f("E0")`."
- *Silent.* Nothing in the output hints that `S` and `W` matched everything. Round 1 had the same
  confusion with `f(E0)`.

**What to change.**
- Keep the pitfall, but move it into the recipes table as a contrast: `select f("B2")` (a value)
  next to `select f(x) where …` (a variable).
- Don't add a heuristic warning, per the project's preference against such messages.
- A factual option: echo what a pattern bound when variables are unused, e.g.
  `$0 = <227 element(s) in 1 trace(s)>, binding S, W`. Decide whether that's worth it.

## 4. Queries in other languages' syntax

**What agents tried.**

| Command | Run | Result |
|---|---|---|
| `select /evaluate/ from calls where args[1] like "%%"` | ex03 | `error: expected 'select'` |
| `select /evaluate/ from calls` | ex03 | the same |
| `select /subtract/(...) raised` | ex09 | `error: expected end of command, found 'raised'` |

**Cause.**
- *Not supported.* The SQL-like form treats `from` as naming a table. In pmdb, `from` takes a
  variable or a nested `select`, which the skill shows once (`select f(x) from $0 where x > 1`).
  `expected 'select'` is accurate but doesn't mention variables.
- `raised` mirrors how pmdb *prints* exceptions (`call f(…) raised {…}`), so it's a natural guess.
  There is no pattern for calls that raised, only the exception snaps
  (`select /subtract\.\$exception/`, which the agent found two commands later).

**What to change.**
- **Add a pattern for calls that raised**, symmetric with `-> r`: e.g. `select f(...) raised e
  where e.type == "IndexError"`, so the printed form is also a query form. This is the one new
  feature this round suggests.
- Make the `from` error name both forms: `error: expected a variable such as $0, or a select`.

## 5. A regex for one function's exception

**What agents tried.** `select /subtract/.*\$exception/` failed with `error: expected end of
command, found '.*\$exception/'`. The agent then used `select /.*\$exception/`, which listed all
four exception snaps.

**Cause.** *Documentation unclear.* The skill's only exception example is `/.*\$exception/`. Snap
labels are `<function>.$exception`, so one function's exception is `/subtract\.\$exception/`.
The error is correct (the regex ends at the second `/`), but the skill never shows the
per-function form.

**What to change.**
- In the skill's recipes, write the exceptions row as `select /subtract\.\$exception/` (one
  function) and `select /.*\$exception/` (all).
- With section 4's `raised` pattern, this becomes `select subtract(...) raised e`.

## 6. Comparing values of different types

**What agents tried.** In ex04, `select evaluate(...) -> r where r == -4` failed with
`error: cannot apply == on values of type 'object' and 'integer'`. Some `evaluate` calls return
values that the recorder pickles (`<object>`). The agent switched to `select evaluate(...) -> -4`,
which worked (4 matches).

**Cause.** *Documented.* The skill says "Values of different types never compare, not even with
`==`" and suggests literal patterns, which is what the agent ended up doing. But the rule fails
the whole query on the first mismatch. In Python traces, where one function returns `0`, `0.5` or
an object depending on the branch, the rule is easy to trip over (round 1: ints against floats).

**What to change (a language decision).** Let `==` and `!=` compare values of different types as
unequal instead of failing, as they already do with `none`. Ordering comparisons (`<`, …) can keep
failing. This is a semantic change to equality, not a special encoding, but it affects every
query, so it's worth deciding explicitly.

## 7. Output volume

**What agents did.**
- 9 `pmdb --show` commands, all cut with `head -100`, `head -200`, `tail -2000 | head -500` or
  `grep -A 100`;
- 3 outputs too large for Claude Code to show inline: 78.5 KB twice (section 3) and 46 KB;
- calls whose first argument is an opaque object printed as `<object>` (`fastest_route(<object>,
  E0, A0)`, `reconstruct(<object>, …)`), which is short but hides the road network.

Feedback asked for "a 'summarize' mode that shows only the function name and result", "built-in
limit/head-like functionality", and "option for compact output showing just results without
source code snippets". No agent used the skill's `clip` script or its `grep -v '^[ >]'` recipe
for dropping excerpts.

**Cause.** *Output problem.*
- `show` always prints five lines of source per match, and arguments in full.
- The skill's workarounds are shell recipes that agents didn't adopt.

**What to change.**
- `show $0 brief`: one `file:line: call … -> …` line per match, with long values elided in the
  middle like `clip`.
- `show $0 limit 20`.
- These turn the skill's two recipes into pmdb features, which agents reach for (`show $0 | head`
  was tried inside pmdb).

## 8. Empty results that look like broken queries

**What agents did.** In ex01, Haiku ran `select spread(amount, weights) where amount > 0`, then
`select /spread/(...)`, then `select spread(...)`. Each printed `$0 = <0 element(s) in 0
trace(s)>`, with `show query` failing after it (section 1). It concluded the queries were wrong
and used `--show | grep`. In fact `spread` is never called in that run: the queries were right.

**Cause.** *Output problem.* An empty result doesn't distinguish "no call of `spread` exists" from
"the pattern or the where clause excluded every call".

**What to change.** When a call pattern's name matches no call at all, say so:
`$0 = <0 element(s)>; no call of 'spread' in the traces`. This is a fact about the trace, cheap to
compute, and would have kept the agent on queries.

## 9. Sonnet doesn't use pmdb on these exercises

Sonnet invoked the skill in 2 of its 10 runs and ran 3 pmdb commands, all successful. Its feedback
explains why: "the bug was visible on direct code read", "the code was small enough that manual
arithmetic … was faster than recording/querying a trace". This is a property of round 1's
exercises more than of pmdb. Round 3 tests exercises built to resist reading.

---

## Round 1's problems, revisited

| Round 1 problem | Round 1 | Round 2 |
|---|---|---|
| 1. Selecting a call's return value | 7 commands, 1 silently empty | **solved**: results show with calls, `-> r` used in 11 commands, none failing because of it |
| 2. Matching arguments by value | 5 commands, 1 silently empty | **mostly solved**: literal patterns used successfully; bare names still silently match everything (section 3) |
| 3. Writing where clauses (quotes, `and`, missing keys) | 5 commands | **solved**: no quote, `and` or key errors; one type mismatch (section 6) |
| 4. `from` clauses | 3 commands | **open**: 2 SQL-like `from calls` (section 4) |
| 5. Running several commands | 5 commands | **changed**: heredocs worked; 7 failures from `$N` numbering and `show query` (section 1), 1 pipe inside the heredoc |
| 6. Command-line usage | 4 commands | **solved**: no failures |
| 7. Output volume and `<object>` | 9 `--show` commands cut | **open**: 9 `--show` commands cut, 3 oversized outputs (section 7) |
| 8. First impression of the documentation | Sonnet never ran pmdb | **partly**: Haiku used the skill every time; Sonnet still mostly skipped pmdb (section 9) |

## Suggested order of work

1. **Fix `*` followed by positional patterns** (section 2). It is a bug that silently returns
   nothing.
2. **Error messages that state what's expected or defined** (sections 1, 4). They're cheap and
   address 10 of the 13 failures.
3. **Say when a call pattern names a function absent from the traces** (section 8).
4. **`show … brief` and `show … limit N`** (section 7), and the per-function exception recipe in
   the skill (section 5).
5. **Decide on cross-type `==`** (section 6) and a `raised` call pattern (section 4).

Each change can be checked by re-running the commands in [pmdb_attempts.md](pmdb_attempts.md):
they should succeed, or fail with an error that names the fix.
