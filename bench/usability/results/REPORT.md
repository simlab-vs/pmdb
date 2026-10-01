# Usability study of pmdb: report

40 runs (10 exercises × 2 arms × 2 models), Claude Code 2.1.283 on the user's subscription. The
models were `claude-sonnet-5` and `claude-haiku-4-5-20251001`, and pmdb was frozen at `a9cb57d`.
The design is in [PROTOCOL.md](../PROTOCOL.md) and was not changed after the start. The full
tables and all feedback are in [summary.md](summary.md), and the per-run records are in
[runs.jsonl](runs.jsonl).

## Headline

In this setting, having pmdb available made agents **slower and more expensive, and never more
successful**. The pre-registered paired comparison (B − A, 20 pairs):

| measure | median B − A | 95% CI | Wilcoxon p |
|---|---|---|---|
| total tokens | +21.5k | +16k to +111k | < 0.001 |
| turns | +1 | 0 to +3 | 0.002 |
| wall time | +11 s | +5 to +14 s | < 0.001 |

Success was 20/20 without pmdb and 19/20 with it (McNemar p = 1.0).

Why, in two parts:
1. **The exercises are too easy for runtime information to matter.** 39 of 40 runs fixed the bug,
   usually in 10–13 turns. Diffing the actual against the expected output and then reading
   100–300 lines of code was enough every time; agents in both arms named that diff as the key
   step. Crash controls were solved straight from the traceback. This is a limit of the exercise
   set, not evidence that pmdb can't help (see "What to change in the study").
2. **pmdb's cost is paid even when it isn't used.** 19 of 20 pmdb-arm runs read
   `/opt/pmdb/README.md`. Sonnet then never ran pmdb (0 of 10 runs) and solved the bug by
   reading code, so those runs only paid for the README (+10k tokens). Haiku ran pmdb in 8 of 10
   runs. Its median cost went from 153k to 276k tokens, and its worst runs (ex01 and ex08) took
   27–32 turns and about 1M tokens.

The only failure is a pmdb-arm run (Haiku, ex01). The agent overfitted to the reported example:
it changed the `BIG50` coupon's data so that the reported output matched. That fixed the reported
input but broke 209 of the 300 hidden inputs. Its pmdb queries had failed, so it fell back to
guessing.

## Usability findings

Ranked by how often they cost agents time. The quotes are from the agents' feedback.

1. **Query syntax that looks reasonable fails, with error messages that don't help.** 15 of 39
   pmdb calls failed:

   | error | count | example query |
   |---|---|---|
   | `expected expression` | 5 | `select subtract(_, _) where _` |
   | `expected identifier` | 4 | `select call(parse, _)`, `select spread(5000, [..])` |
   | `multiple commands should be separated by a newline` | 3 | `select /utilization/\.\$result/` |
   | `expected '…'` | 2 | `select spread(*) from * where true` |
   | `undefined symbol` | 2 | `show $0` in a fresh `-e` invocation |

   Agents wrote literal values as argument patterns (`spread(5000, …)`) and used `_` inside where
   clauses. They assumed `$0` survives between invocations, and they piped commands with `|`. The
   errors give no position, expected form or example: *"Error messages didn't suggest what the
   correct syntax should be."*
2. **Return values are hard to reach.** Every Haiku run that used pmdb wanted the result of a
   call. A call's result is a *separate snap* labeled `f.$result`, which needs a regex such as
   `/f\.\$result/`. The obvious `f.$result` and `f(_).$result` fail with the misleading "multiple
   commands" error. Wishes: *"Side-by-side display of call arguments and return values"*, *"a
   simpler interface for inspecting return values"*.
3. **The documentation doesn't teach debugging use.** Agents believed features were missing
   that exist: *"No way to filter results by argument values"* (where clauses do this) and
   *"Unclear how to query for return values"*. The README describes the grammar but gives few
   task-shaped examples. Its "under development" note made one agent distrust the tool.
   Sonnet: *"the query language … looked non-trivial to construct correctly on the first try …
   compared to just reading the ~130-line source file directly."*
4. **`--show` and listings are too verbose to use.** When queries failed, agents fell back to
   `pmdb --show` and grepped hundreds of lines (*"extremely verbose"*, in 6 runs). They asked for
   filtering, collapsing and "only the results of function X".
5. **Each `-e` invocation starts from scratch.** `$0` from an earlier call is undefined
   (`undefined symbol '$0'`). Several agents tried piping `select … | show $0` into one process.
6. **Missing comparison features (asked for in several forms).** Agents asked for a trace diff
   ("highlight the first call whose return value diverges"), expected-vs-actual divergence
   detection, and per-call cost breakdowns for numeric bugs (routes: turn penalties).

What worked: when a Haiku query did succeed, the trace directly showed the faulty behaviour.
In ex04 it showed `||` evaluating the left operand twice, and in ex07 the equal-cost paths. Both
times it was named as the key step. The recorder and the trace recorded in advance worked in
every run. No agent used `pmdb-record`, because the trace was already there.

## Recommendations for pmdb

1. **Make return values first-class.** Show `→ result` next to each call in listings and
   `show`, and allow `f(...).$result` or `select f(x) where result == …`.
2. **Errors that teach.** Report the column, what was expected, and a corrected example
   (e.g. "`_` cannot be used in an expression; bind a name: `f(x) where x > 0`"). Special-case
   literals in argument patterns and dots in labels.
3. **A README with a "debugging recipes" section first:**
   - all calls to `f` with their results;
   - calls where an argument has a value;
   - calls whose result differs from an expectation;
   - the calls inside one call.

   Put the grammar after it.
4. **Allow several `-e` commands per process in a single argument (`;`-separated)**, or keep
   variables across invocations. At least, make the `undefined symbol '$0'` error mention that
   variables don't persist.
5. **Filtering and output limits for `--show`** (by function, depth, or "only results").
6. **Later: a trace diff** between two runs, or against expected values.

## What to change in the study

The harness worked. The sandbox, mechanical bug generation, hidden grading (which caught the
overfitted fix) and in-session feedback all did their job. To measure where pmdb *can* help:

- **Harder exercises.** Bigger programs where reading everything is expensive, bugs far from the
  symptom, and outputs that don't localize the fault when diffed. The rare/subtle categories here
  were rare per input file, yet still trivially localized by diffing the output.
- **Pay the README cost once.** Give a short task-oriented quick reference instead of the full
  README, or measure README reading separately.
- **Re-run after pmdb changes** on the same exercises, to isolate the effect of the usability
  fixes. Use new exercises for any claim about efficiency.

## Limitations

- The programs were written by the model family under study (Claude), though no bug was placed
  by hand.
- Each condition ran once. The models are the subscription's aliases, with default effort.
- The token difference is significant but small in absolute terms, and it is driven by the cost
  of reading the documentation and by Haiku's failed queries.
- `pmdb_failed` counts tool results that contain `error:`; it may slightly over- or undercount.
