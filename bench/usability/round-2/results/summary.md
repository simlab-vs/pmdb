# Usability study of pmdb: results

40 runs, 20 complete exercise × model pairs.

Resolved models: claude-haiku-4-5-20251001, claude-sonnet-5.

## Runs

| exercise | model | arm | success | localized | turns | tokens (k) | wall (s) | pmdb / record calls (failed) |
|---|---|---|---|---|---|---|---|---|
| ex01-invoicing-rare | haiku | A | ✓ | ✓ | 13 | 226 | 66 | 0 / 0 (0) |
| ex01-invoicing-rare | haiku | B | ✓ | ✓ | 18 | 389 | 91 | 7 / 0 (3) |
| ex01-invoicing-rare | sonnet | A | ✓ | ✓ | 10 | 218 | 85 | 0 / 0 (0) |
| ex01-invoicing-rare | sonnet | B | ✓ | ✓ | 12 | 260 | 55 | 2 / 0 (0) |
| ex02-invoicing-subtle | haiku | A | ✓ | ✓ | 12 | 157 | 24 | 0 / 0 (0) |
| ex02-invoicing-subtle | haiku | B | ✓ | ✓ | 13 | 223 | 26 | 2 / 0 (1) |
| ex02-invoicing-subtle | sonnet | A | ✓ | ✓ | 8 | 123 | 17 | 0 / 0 (0) |
| ex02-invoicing-subtle | sonnet | B | ✓ | ✓ | 8 | 141 | 49 | 0 / 0 (0) |
| ex03-calc-rare | haiku | A | ✓ | ✓ | 10 | 99 | 18 | 0 / 0 (0) |
| ex03-calc-rare | haiku | B | ✓ | ✓ | 20 | 361 | 41 | 4 / 0 (3) |
| ex03-calc-rare | sonnet | A | ✓ | ✓ | 8 | 122 | 19 | 0 / 0 (0) |
| ex03-calc-rare | sonnet | B | ✓ | ✓ | 10 | 121 | 17 | 0 / 0 (0) |
| ex04-calc-subtle | haiku | A | ✓ | ✓ | 12 | 155 | 36 | 0 / 0 (0) |
| ex04-calc-subtle | haiku | B | ✓ | ✓ | 19 | 465 | 58 | 7 / 0 (3) |
| ex04-calc-subtle | sonnet | A | ✓ | ✓ | 10 | 128 | 18 | 0 / 0 (0) |
| ex04-calc-subtle | sonnet | B | ✓ | ✓ | 8 | 143 | 18 | 0 / 0 (0) |
| ex05-scheduler-rare | haiku | A | ✓ | ✓ | 13 | 181 | 32 | 0 / 0 (0) |
| ex05-scheduler-rare | haiku | B | ✓ | ✓ | 15 | 233 | 33 | 2 / 0 (0) |
| ex05-scheduler-rare | sonnet | A | ✓ | ✓ | 10 | 145 | 19 | 0 / 0 (0) |
| ex05-scheduler-rare | sonnet | B | ✓ | ✓ | 7 | 165 | 20 | 0 / 0 (0) |
| ex06-scheduler-subtle | haiku | A | ✓ | ✓ | 15 | 252 | 57 | 0 / 0 (0) |
| ex06-scheduler-subtle | haiku | B | ✓ | ✓ | 15 | 334 | 122 | 2 / 0 (0) |
| ex06-scheduler-subtle | sonnet | A | ✓ | ✓ | 10 | 129 | 28 | 0 / 0 (0) |
| ex06-scheduler-subtle | sonnet | B | ✓ | ✓ | 9 | 232 | 186 | 0 / 0 (0) |
| ex07-routes-rare | haiku | A | ✓ | ✓ | 12 | 187 | 45 | 0 / 0 (0) |
| ex07-routes-rare | haiku | B | ✓ | ✓ | 20 | 510 | 159 | 6 / 0 (2) |
| ex07-routes-rare | sonnet | A | ✓ | ✓ | 14 | 305 | 120 | 0 / 0 (0) |
| ex07-routes-rare | sonnet | B | ✓ | ✓ | 13 | 273 | 68 | 1 / 0 (0) |
| ex08-routes-subtle | haiku | A | ✓ | ✓ | 13 | 232 | 89 | 0 / 0 (0) |
| ex08-routes-subtle | haiku | B | ✓ | ✓ | 17 | 391 | 124 | 4 / 0 (0) |
| ex08-routes-subtle | sonnet | A | ✓ | ✓ | 9 | 140 | 38 | 0 / 0 (0) |
| ex08-routes-subtle | sonnet | B | ✓ | ✓ | 8 | 135 | 54 | 0 / 0 (0) |
| ex09-scheduler-crash | haiku | A | ✓ | ✓ | 11 | 129 | 14 | 0 / 0 (0) |
| ex09-scheduler-crash | haiku | B | ✓ | ✓ | 17 | 279 | 32 | 5 / 0 (2) |
| ex09-scheduler-crash | sonnet | A | ✓ | ✓ | 8 | 121 | 15 | 0 / 0 (0) |
| ex09-scheduler-crash | sonnet | B | ✓ | ✓ | 8 | 140 | 12 | 0 / 0 (0) |
| ex10-routes-crash | haiku | A | ✓ | ✓ | 13 | 167 | 25 | 0 / 0 (0) |
| ex10-routes-crash | haiku | B | ✓ | ✓ | 15 | 229 | 30 | 2 / 0 (0) |
| ex10-routes-crash | sonnet | A | ✓ | ✓ | 9 | 123 | 17 | 0 / 0 (0) |
| ex10-routes-crash | sonnet | B | ✓ | ✓ | 9 | 167 | 16 | 0 / 0 (0) |

## Pre-registered comparisons (B − A, paired)

- **total tokens**: median difference +56848 (95% CI +19321 to +127088), Wilcoxon W+ = 200.0, n = 20, p = 0.000
- **turns**: median difference +2 (95% CI +0 to +3), Wilcoxon W+ = 111.5, n = 16, p = 0.022
- **wall time (s)**: median difference +11 (95% CI +0 to +24), Wilcoxon W+ = 148.0, n = 19, p = 0.032
- **success**: A 20/20, B 20/20; only B: 0, only A: 0, exact McNemar p = 1.000
- **localized**: A 20/20, B 20/20

## Descriptive breakdowns

| group | pairs | success A | success B | median tokens A (k) | median tokens B (k) | median turns A | median turns B |
|---|---|---|---|---|---|---|---|
| category crash | 4 | 4 | 4 | 126 | 198 | 10 | 12 |
| category rare | 8 | 8 | 8 | 184 | 266 | 11 | 14 |
| category subtle | 8 | 8 | 8 | 147 | 228 | 11 | 11 |
| model haiku | 10 | 10 | 10 | 174 | 347 | 12 | 17 |
| model sonnet | 10 | 10 | 10 | 129 | 154 | 10 | 8 |

## pmdb usage in arm B

pmdb or pmdb-record used in 12/20 runs; 44 pmdb calls, 0 pmdb-record calls, 14 failed.

### Error messages printed by pmdb

- 4× `error: expected variable` (e.g. `pmdb /work/report.pmdb <<'EOF'
select spread(amount, weights) where amount > 0
show query
EOF
`)
- 3× `error: undefined symbol '…'` (e.g. `pmdb report.pmdb <<'EOF'
select spread(*, *)
show $1
EOF
`)
- 2× `error: expected end of command, found '…'` (e.g. `pmdb /work/report.pmdb <<'EOF'
select fastest_route(...) -> r where r.len() > 0
show $0 | head -40
EOF
`)
- 2× `error: expected '…'` (e.g. `pmdb /work/report.pmdb <<'EOF'
select /evaluate/ from calls where args[1] like "%%" 
show --query
EOF
`)
- 1× `error: expected end of command, found '.*` (e.g. `pmdb /work/report.pmdb <<'EOF'
select /subtract/.*\$exception/
show $1
EOF
`)
- 1× `error: cannot apply == on values of type '…' and '…'` (e.g. `pmdb /work/report.pmdb <<'EOF'
select evaluate(...) -> r where r == -4
show $1
EOF
`)
- 1× `error: {e}` (e.g. `pmdb /work/report.pmdb <<'EOF'
select evaluate(...) -> -4
show $0
EOF
`)

## Feedback

- pmdb_usefulness (arm B): median 2.5, values [1, 1, 2, 2, 2, 2, 3, 3, 4, 4, 4, 4]
- confidence (arm A): median 5.0, values [4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
- confidence (arm B): median 5.0, values [4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

### pmdb_problems

- [B haiku ex01-invoicing-rare] Query syntax errors like 'expected variable' were unhelpful and didn't explain what went wrong
- [B haiku ex01-invoicing-rare] Early attempts at select queries didn't work; unclear which function names to use without seeing the trace structure first
- [B sonnet ex01-invoicing-rare] Had to manually recompute expected arithmetic by hand since pmdb's query language lacks sums/folds, so I couldn't directly ask 'show me the subtotal before and after volume discount for this line' without reading the trace and doing the math myself
- [B sonnet ex01-invoicing-rare] No direct way to ask 'which function produced a value that differs from recompute-by-formula' — had to narrow down call by call (invoice -> coupon_reductions) rather than jumping straight to volume_discount_rate
- [B haiku ex02-invoicing-subtle] Query syntax was initially unclear ($1 vs $0); the error message didn't guide me to the right variable name.
- [B haiku ex02-invoicing-subtle] The output showed function calls and results but didn't highlight the logical issue (leftover not being distributed).
- [B haiku ex03-calc-rare] Query syntax was unclear; `select /evaluate/ from calls` and `select evaluate(...) -> r where r == 60` both failed with confusing error messages
- [B haiku ex03-calc-rare] The --show output was extremely long and difficult to navigate even when piped to head
- [B haiku ex03-calc-rare] Unclear how to write a simple query for 'show all calls to function X' or 'show evaluation of line 3'
- [B haiku ex04-calc-subtle] Type comparison errors are unhelpful—when I queried 'where r == -4' on object results, it failed with a confusing 'cannot apply ==' message instead of narrowing results
- [B haiku ex04-calc-subtle] The pmdb --show output for large traces is extremely verbose and hard to navigate without heavy filtering
- [B haiku ex04-calc-subtle] Query result variable numbering ($0 vs $1) required trial-and-error to understand
- [B haiku ex05-scheduler-rare] Output was verbose with many repeated function calls (busy_intervals called 6 times) that cluttered the results
- [B haiku ex05-scheduler-rare] Queries showed what functions returned but not intermediate variable values inside the function, which would have been useful
- [B haiku ex06-scheduler-subtle] Output was verbose when multiple rooms were involved; had to scroll through results for all 3 rooms to find R3's data
- [B haiku ex06-scheduler-subtle] No built-in filtering, so I had to parse through all free_slots and busy_intervals calls rather than querying R3-specific ones
- [B haiku ex07-routes-rare] Cannot query local variables like the `previous` dictionary that store the algorithm's state
- [B haiku ex07-routes-rare] Piping/filtering syntax doesn't work as expected inside pmdb commands (tried `| head`)
- [B haiku ex07-routes-rare] The inline display of full function arguments and source context makes output verbose for large traces
- [B sonnet ex07-routes-rare] The query I ran (select fastest_route(...) -> r) just reproduced the known buggy output; it didn't help pinpoint why <= vs < mattered since that requires reasoning about the algorithm's tie-breaking logic, not inspecting specific call arguments/returns.
- [B sonnet ex07-routes-rare] There's no straightforward way to query 'did this value get overwritten by a later equal-cost update' which was the actual root cause — that's a property of control flow/invariant over time, not a single call's arguments or result.
- [B haiku ex08-routes-subtle] Query results were extremely large even with specific filters, making output hard to scan
- [B haiku ex08-routes-subtle] No built-in truncation for large result sets; had to rely on external piping
- [B haiku ex08-routes-subtle] Difficult to isolate turn penalties that were actually used in the winning paths vs. exploratory paths
- [B haiku ex09-scheduler-crash] Error messages for invalid syntax were unhelpful (e.g., 'expected end of command, found raised')
- [B haiku ex09-scheduler-crash] Documentation mentioned querying exceptions but the actual syntax pattern was unclear

### pmdb_wishes

- [B haiku ex01-invoicing-rare] A simpler built-in command like 'list all calls' to see what's in the trace without needing to --show and grep
- [B haiku ex01-invoicing-rare] Better error messages that explain the syntax mistake (e.g., 'pattern missing arguments' or 'function not found')
- [B sonnet ex01-invoicing-rare] A query mode that could evaluate a user-supplied reference formula against recorded arguments to flag any mismatching calls in one shot (e.g. 'select line_subtotal(l) -> s where s != l.unit_price*l.quantity - expected_discount(l)')
- [B sonnet ex01-invoicing-rare] Easier chaining to jump from a wrong field in a parent's result straight to the specific child call that produced it, without re-querying by exact argument values
- [B haiku ex02-invoicing-subtle] Could flag invariant violations, e.g., 'leftover is 2 but shares were not incremented'
- [B haiku ex02-invoicing-subtle] Could suggest suspicious patterns like '+= 0' in an increment loop
- [B haiku ex03-calc-rare] A quick-start example showing how to query a specific function by name
- [B haiku ex03-calc-rare] Better error messages that suggest correct syntax when a query fails
- [B haiku ex03-calc-rare] A simpler query mode or helper for common tasks like 'find all calls to evaluate' without learning full syntax
- [B haiku ex04-calc-subtle] Automatic type inference/coercion in where clauses to avoid type mismatch errors
- [B haiku ex04-calc-subtle] A 'summarize' mode that shows only the function name and result without full arguments for large traces
- [B haiku ex04-calc-subtle] Better filtering options before results are displayed
- [B haiku ex05-scheduler-rare] Ability to query local variable values at specific points in a function execution
- [B haiku ex05-scheduler-rare] Better filtering/deduplication of repeated calls to the same function
- [B haiku ex05-scheduler-rare] Trace a specific function call path rather than all invocations
- [B haiku ex06-scheduler-subtle] Query filtering by argument values (e.g., 'free_slots calls where first arg contains "R3"')
- [B haiku ex06-scheduler-subtle] Formatted output highlighting for key values or differences from window/interval boundaries
- [B haiku ex07-routes-rare] Ability to inspect local variable state at specific function calls
- [B haiku ex07-routes-rare] Integration with standard Unix pipes for output filtering
- [B haiku ex07-routes-rare] Option for compact output showing just results without source code snippets
- [B sonnet ex07-routes-rare] A way to query how many times a given state/key was written to a dict across a function's execution, to directly surface overwrite-on-tie bugs like this one.
- [B sonnet ex07-routes-rare] Guidance in the skill docs for debugging algorithmic/tie-breaking bugs where costs match but paths differ, as opposed to bugs where a returned value is simply wrong.
- [B haiku ex08-routes-subtle] Built-in limit/head-like functionality for large result sets
- [B haiku ex08-routes-subtle] Ability to filter by result range (e.g., only turn_penalty calls returning 26)
- [B haiku ex08-routes-subtle] Option to trace only calls in the final reconstructed path
- [B haiku ex09-scheduler-crash] Better error messages for syntax errors with hints about correct syntax
- [B haiku ex09-scheduler-crash] Simpler syntax for querying exceptions/errors
- [B haiku ex09-scheduler-crash] More examples in docs for common exception queries
- [B haiku ex10-routes-crash] A quick command to show only the call(s) that raised exceptions, without needing to select first
- [B haiku ex10-routes-crash] Direct link to the exact code line where the exception originated, not just the caller's line

### other_wishes

- [A sonnet ex01-invoicing-rare] A quick way to diff per-field structured output (e.g. JSON) rather than formatted text, so the exact row/field that mismatches is immediately obvious without manual line-matching
- [A sonnet ex01-invoicing-rare] An inline assertion/property-based test harness for pure functions like basis_points and volume_discount_rate would have caught the boundary bug faster than manual tracing
- [A haiku ex04-calc-subtle] A diff view between actual and expected output would have highlighted the specific line faster
- [A haiku ex04-calc-subtle] pdb would have been useful to step through the evaluation of the problematic expression to confirm the bug before reading the source code
- [A sonnet ex05-scheduler-rare] None needed here — the bug was simple enough that reading the small codebase plus a diff of outputs was sufficient; a debugger would have been overkill for a single off-by-one constant.
- [A haiku ex06-scheduler-subtle] A test suite or unit tests for the subtract function would have made me more confident in edge cases beyond what the provided test case covers
- [A sonnet ex06-scheduler-subtle] A quick way to pretty-print intermediate values of busy_intervals()/subtract() per room without manually inserting print statements or firing up pdb, since the bug was in a small pure function and manual trace-by-hand was the main time cost
- [A sonnet ex07-routes-rare] A small script/REPL helper to quickly compute the seconds-cost of an arbitrary path given a network and turn-penalty function would have saved time versus writing one ad hoc from scratch.
- [A sonnet ex08-routes-subtle] A way to auto-generate per-trip expected intermediate values (edge times, turn penalties) to shortcut the manual arithmetic tracing I had to do by hand
- [B sonnet ex01-invoicing-rare] A direct way to diff expected vs actual output and have it point to the exact row/field with the discrepancy, saving the initial manual diff-reading step
- [B haiku ex02-invoicing-subtle] A direct diff of expected vs actual output highlighting which lines/values differ would have immediately pinpointed order 3-0
- [B haiku ex02-invoicing-subtle] A simple linter rule to catch `+= 0` or `+= false` as likely typos
- [B sonnet ex02-invoicing-subtle] None needed here — the bug was visible on direct code read and confirmed by a simple diff of actual vs expected output, so no additional tooling was necessary.
- [B haiku ex04-calc-subtle] The diff output was the most immediately useful—a simpler approach might have been just reading evaluator.py carefully once I knew line 12 was wrong, rather than tracing through execution
- [B haiku ex05-scheduler-rare] A quick way to inspect variable values at any line during execution (traditional debugger-style)
- [B sonnet ex05-scheduler-rare] None needed here — the bug was visible from a straightforward read of the small, well-documented utilization() function once the diff narrowed the problem to one specific stat.
- [B haiku ex06-scheduler-subtle] A diff output mode that highlights the first line where actual differs from expected
- [B haiku ex07-routes-rare] For algorithm bugs, a tool that directly compares two execution traces side-by-side
- [B haiku ex07-routes-rare] Guidance on when to use trace debugging vs code inspection for different bug types
- [B sonnet ex07-routes-rare] A reference correct implementation or spec for the turn-penalty routing algorithm would have let me confirm the tie-breaking convention (first-found vs. last-found) without having to infer it from expected_output.txt alone.
- [B haiku ex08-routes-subtle] For this specific task, simple print-based debugging or manual calculation would have been faster than pmdb
- [B haiku ex08-routes-subtle] A tool to annotate the expected vs. actual output showing which values differed and by how much
- [B sonnet ex08-routes-subtle] None needed here — the code was small enough that manual arithmetic on the known expected route was faster than recording/querying a trace.
- [B haiku ex10-routes-crash] The initial Python traceback already pinpointed the problematic line; a tool suggesting related test cases or showing which inputs trigger that code path would have accelerated the debugging
- [B sonnet ex10-routes-crash] None needed here — the traceback plus a quick read of the ~60 lines of source was sufficient; pmdb would likely help more on bugs without a crashing traceback or with wrong-but-not-crashing output.

### wasted_effort

- [A sonnet ex01-invoicing-rare] I did a fair amount of manual arithmetic by hand to recompute basis_points and rounding, and made an arithmetic slip (treating 40*500/10000 as 0.2 instead of 2) that briefly led me down a wrong path before I just ran the actual functions in Python to get precise intermediate values.
- [A haiku ex07-routes-rare] I manually traced through both paths and calculated costs including turn penalties to verify they were equal—this confirmed my understanding but wasn't necessary to identify the bug, which was visible in the code logic.
- [A sonnet ex07-routes-rare] I spent some time reasoning about whether the heap's tuple tie-breaking order (by node name/heading) explained the discrepancy before realizing the simpler explanation: the `previous` dict was being overwritten on cost ties regardless of heap order.
- [B haiku ex01-invoicing-rare] I spent time trying pmdb query syntax (select spread, select volume_discount_rate) that failed with 'expected variable' errors. This was a dead end—I should have jumped straight to pmdb --show which gave the full trace.
- [B sonnet ex01-invoicing-rare] I initially spent time hypothesizing that the BIG50 coupon's spread() logic was incorrectly applying a reduction, and manually computed what a full coupon application would look like before ruling it out — this was reasonable but took a couple of extra calculation steps before I checked the actual threshold comparison.
- [B haiku ex02-invoicing-subtle] The pmdb queries—I invoked pmdb but the bug was obvious from static code inspection, so the tracing and querying added little value for a simple typo.
- [B haiku ex03-calc-rare] I attempted several pmdb queries that failed with syntax errors before giving up and reading the code directly, which revealed the bug in seconds.
- [B haiku ex04-calc-subtle] Attempted a pmdb query with type comparison (where r == -4) that failed with an unhelpful type mismatch error; had to navigate a very large pmdb --show output before learning to query more specifically.
- [B haiku ex05-scheduler-rare] Running pmdb queries to examine the utilization function calls. I had already identified the bug from reading the code, and the pmdb output confirmed the symptom (returning 22) but didn't help locate the root cause faster than code inspection did.
- [B haiku ex07-routes-rare] I spent significant time setting up and running pmdb queries (about 5 attempts) that examined the reconstructed paths and path lengths. These confirmed the symptom but didn't directly reveal the root cause. A more direct reading of the algorithm code would have been faster.
- [B sonnet ex07-routes-rare] I invoked the pmdb skill and queried the pre-recorded trace, but it only confirmed the already-known output (cost and path) without revealing anything pmdb couldn't have shown via a plain Python run; the actual diagnosis came from manual arithmetic, not from the trace.
- [B haiku ex08-routes-subtle] Extensive pmdb queries that returned very large outputs (78.5KB) with hundreds of turn penalties. The large result sets didn't help narrow down the problem—the fix came from simple arithmetic rather than trace analysis.
- [B haiku ex09-scheduler-crash] Spent a few minutes trying incorrect pmdb query syntax (using 'raised' keyword, complex regex patterns) before finding the correct format. Could have just read the code and spotted the bug immediately.

### key_step

- [A haiku ex01-invoicing-rare] The diff output showing SKU-146 net as 0.40 (actual) vs 0.39 (expected) pinpointed the exact problem. Combined with noticing that SKU-146 had quantity 10 and the VOLUME_TIERS list contained (10, 200), I recognized the threshold comparison was likely using > instead of >=.
- [A sonnet ex01-invoicing-rare] Noticing that SKU-146 had quantity=10, exactly equal to a VOLUME_TIERS threshold (10, 200bps), and recognizing the docstring says 'minimum quantity' which implies the boundary should qualify, while the code used strict '>' instead of '>='.
- [A haiku ex02-invoicing-subtle] Using diff to compare expected vs actual output, which revealed that only 2 cents were missing and only in the first order (which had a coupon), immediately suggesting the bug was in coupon discount distribution logic.
- [A sonnet ex02-invoicing-subtle] Noticing that only the order using the 'BIG50' fixed coupon (which triggers spread()) had mismatched output, combined with spotting the dead '+= 0' line in spread() during code review.
- [A haiku ex03-calc-rare] Noticing the `!= -1` in the `||` operator implementation at evaluator.py:118, which should have been `!= 0` to correctly evaluate truthiness.
- [A sonnet ex03-calc-rare] Reading the evaluator.py source and spotting that the `||` branch compared the right-hand evaluation to `-1` instead of `0`, which stood out as inconsistent with the `&&` branch right above it.
- [A haiku ex04-calc-subtle] Reading line 118 of evaluator.py and noticing it evaluated tree[2] for the || operator while the && operator correctly used tree[3], which was inconsistent and clearly wrong for binary operator evaluation.
- [A sonnet ex04-calc-subtle] Diffing actual vs expected output narrowed the failure to one specific line/expression, and that line's use of `||` directed me straight to the short-circuit evaluation code where the copy-paste bug (tree[2] instead of tree[3]) was visually obvious.
- [A haiku ex05-scheduler-rare] Running diff between expected and actual output showed the single-line difference in R1's utilization percentage, which directed me to the exact function and line to inspect.
- [A sonnet ex05-scheduler-rare] Diffing actual vs expected output immediately isolated the bug to one specific number (R1 utilization), which pointed straight at the utilization() function instead of the many other functions involved.
- [A haiku ex06-scheduler-subtle] The diff output clearly showed the two discrepancies: R2 Monday and R3 Thursday were both showing free time extending to 18:00 when they should stop at 17:30. This pattern immediately suggested bookings starting late in the day were not being subtracted.
- [A sonnet ex06-scheduler-subtle] The diff output pinpointing exactly which two lines differed (free slot end times both wrongly extended to window close), which directed attention straight to subtract()'s handling of busy intervals that cross the window boundary.
- [A haiku ex07-routes-rare] Running `diff expected_output.txt <(python3 main.py input.json)` revealed that both outputs had the same time (5m32s) but different routes, immediately indicating the bug was in path selection, not cost calculation.
- [A sonnet ex07-routes-rare] Noticing that the actual and expected outputs had identical total times (332s) but different routes, which ruled out an arithmetic bug and pointed directly at the tie-breaking logic (`<=` vs `<`) in the Dijkstra relaxation step.
- [A haiku ex08-routes-subtle] Manually calculating the turn penalties for the two failing routes showed that B2→A0 should be 223s not 224s (1s off), and D2→A0 should be 292s not 294s (2s off). Since the second route had two left turns and the discrepancies were consistent with reducing left turns by 1 second, this pointed directly to the turn_penalty function.
- [A sonnet ex08-routes-subtle] Noticing that the output routes and street descriptions were identical to expected but the total seconds were off by small consistent amounts, which pointed to an arithmetic constant bug (turn penalty) rather than a pathfinding/logic bug.
- [A haiku ex09-scheduler-crash] Running the program and reading the traceback that pinpointed line 33 in availability.py with 'IndexError: list index out of range' on the busy[i] access.
- [A sonnet ex09-scheduler-crash] The traceback from directly running the program, which pinpointed `availability.py` line 33 (`busy[i][0]`) as the IndexError site.
- [A haiku ex10-routes-crash] The traceback showing the IndexError at line 52 in the describe function's conditional that tried to access directions[-2][1]—this immediately revealed both the location and nature of the bug.
- [A sonnet ex10-routes-crash] Running the program and reading the traceback, which pinpointed the exact failing line (directions[-2][1] in describe()).
- [B haiku ex01-invoicing-rare] Using pmdb --show to see the full trace and spotting the line 'call volume_discount_rate(10) -> 0' for an item with quantity 10, which immediately revealed the bug when compared against VOLUME_TIERS.
- [B sonnet ex01-invoicing-rare] Querying coupon_reductions via pmdb to rule out the coupon as the cause, which narrowed the bug down to line_subtotal/volume_discount_rate, combined with noticing SKU-146 had quantity exactly equal to a volume tier threshold (10).
- [B haiku ex02-invoicing-subtle] Reading the spread function code and noticing line 88 said `shares[i] += 0` instead of `shares[i] += 1`, which is obviously a typo in a loop meant to distribute leftover cents.
- [B sonnet ex02-invoicing-subtle] Reading the spread() function source and noticing 'shares[i] += 0' which is a no-op that can't possibly distribute leftover cents as the docstring claims.
- [B haiku ex03-calc-rare] Reading evaluator.py line 118 and spotting that the || operator checks `!= -1` while the && operator on line 116 checks `!= 0`, making the inconsistency immediately obvious.
- [B sonnet ex03-calc-rare] Noticing that only the expression containing || differed from expected output, then reading the evaluate() function's handling of the || operator line by line.
- [B haiku ex04-calc-subtle] Examining the pmdb output showing three evaluate() calls returning -4, particularly the stack trace that pointed to lines 116-119 in evaluator.py, which made me compare how the `&&` and `||` operators differ—the asymmetry (tree[3] vs tree[2]) immediately revealed the bug.
- [B sonnet ex04-calc-subtle] Reading the evaluate() function's handling of the '||' binary operator and noticing it called evaluate(tree[2], ...) instead of evaluate(tree[3], ...), re-evaluating the left operand instead of the right one.
- [B haiku ex05-scheduler-rare] Reading the utilization function source code and seeing `covered = 1` used to accumulate busy minutes - clearly wrong initialization for a sum.
- [B sonnet ex05-scheduler-rare] Noticing that `covered = 1` was used as the initial accumulator value instead of 0 in utilization() — an off-by-one that only affected the final percentage via floor division.
- [B haiku ex06-scheduler-subtle] Querying pmdb for busy_intervals(R3) revealed [5370, 5799], a booking starting at Thursday 17:30. Combined with the fact that free_slots was returning [4800, 5400] (entire Thursday), this made it clear the busy interval wasn't being processed despite overlapping with the window.
- [B sonnet ex06-scheduler-subtle] Diffing actual vs expected output to localize the bug to exactly two 'free until 18:00' lines, then noticing both corresponded to bookings that ran past closing time.
- [B haiku ex07-routes-rare] Reading line 28 of planner.py and noticing the `<=` operator instead of `<`, then manually tracing through the algorithm logic to understand how this causes equal-cost paths to overwrite each other in the `previous` dictionary, leading to non-deterministic behavior when multiple paths have the same total cost.
- [B sonnet ex07-routes-rare] Computing the expected path's cost by hand and finding it exactly equal to the buggy path's cost (332s), which ruled out an arithmetic/logic bug in cost calculation and pointed straight at tie-breaking in the relaxation condition.
- [B haiku ex08-routes-subtle] Manually verifying that the first trip had one left turn and was off by 1 second, while the third trip had two left turns and was off by 2 seconds. This pattern directly pointed to the left turn penalty value (26 vs 25) being the issue.
- [B sonnet ex08-routes-subtle] Noticing that the time discrepancy for each trip was proportional to the number of left turns in that trip's route (1 left turn -> off by 1, 2 left turns -> off by 2), which pinned the bug to the left-turn penalty constant.
- [B haiku ex09-scheduler-crash] Querying pmdb with `select /subtract/(...)` and viewing the results showed the exact arguments (window=[3360, 3960], busy with 4 elements) that caused the crash at the bounds check.
- [B sonnet ex09-scheduler-crash] Running the program directly produced a Python traceback with the exact file, function, and line number of the crash, which immediately revealed the off-by-one bound in the while loop condition.
- [B haiku ex10-routes-crash] Using pmdb to show all describe() calls revealed that the failing input had the same street appearing twice consecutively. This made it immediately obvious the bug was in the merging logic—trying to access directions[-2] when the list was too short.
- [B sonnet ex10-routes-crash] The traceback from simply running the program, which pinpointed the exact line and showed directions[-2][1] being accessed on a single-element list.
