# Usability study of pmdb: results

40 runs, 20 complete exercise × model pairs.

Resolved models: claude-haiku-4-5-20251001, claude-sonnet-5.

## Runs

| exercise | model | arm | success | localized | turns | tokens (k) | wall (s) | pmdb / record calls (failed) |
|---|---|---|---|---|---|---|---|---|
| ex01-invoicing-rare | haiku | A | ✓ | ✓ | 12 | 196 | 89 | 0 / 0 (0) |
| ex01-invoicing-rare | haiku | B | ✗ | ✗ | 27 | 964 | 345 | 8 / 0 (3) |
| ex01-invoicing-rare | sonnet | A | ✓ | ✓ | 10 | 158 | 31 | 0 / 0 (0) |
| ex01-invoicing-rare | sonnet | B | ✓ | ✓ | 9 | 147 | 32 | 0 / 0 (0) |
| ex02-invoicing-subtle | haiku | A | ✓ | ✓ | 11 | 139 | 22 | 0 / 0 (0) |
| ex02-invoicing-subtle | haiku | B | ✓ | ✓ | 18 | 306 | 33 | 6 / 0 (2) |
| ex02-invoicing-subtle | sonnet | A | ✓ | ✓ | 8 | 122 | 20 | 0 / 0 (0) |
| ex02-invoicing-subtle | sonnet | B | ✓ | ✓ | 9 | 139 | 18 | 0 / 0 (0) |
| ex03-calc-rare | haiku | A | ✓ | ✓ | 13 | 146 | 22 | 0 / 0 (0) |
| ex03-calc-rare | haiku | B | ✓ | ✓ | 12 | 134 | 24 | 0 / 0 (0) |
| ex03-calc-rare | sonnet | A | ✓ | ✓ | 10 | 126 | 11 | 0 / 0 (0) |
| ex03-calc-rare | sonnet | B | ✓ | ✓ | 11 | 144 | 20 | 0 / 0 (0) |
| ex04-calc-subtle | haiku | A | ✓ | ✓ | 12 | 136 | 22 | 0 / 0 (0) |
| ex04-calc-subtle | haiku | B | ✓ | ✓ | 15 | 269 | 34 | 4 / 0 (1) |
| ex04-calc-subtle | sonnet | A | ✓ | ✓ | 10 | 128 | 12 | 0 / 0 (0) |
| ex04-calc-subtle | sonnet | B | ✓ | ✓ | 11 | 147 | 25 | 0 / 0 (0) |
| ex05-scheduler-rare | haiku | A | ✓ | ✓ | 12 | 159 | 34 | 0 / 0 (0) |
| ex05-scheduler-rare | haiku | B | ✓ | ✓ | 18 | 279 | 39 | 5 / 0 (3) |
| ex05-scheduler-rare | sonnet | A | ✓ | ✓ | 10 | 145 | 15 | 0 / 0 (0) |
| ex05-scheduler-rare | sonnet | B | ✓ | ✓ | 11 | 167 | 27 | 0 / 0 (0) |
| ex06-scheduler-subtle | haiku | A | ✓ | ✓ | 16 | 259 | 49 | 0 / 0 (0) |
| ex06-scheduler-subtle | haiku | B | ✓ | ✓ | 15 | 274 | 96 | 2 / 0 (1) |
| ex06-scheduler-subtle | sonnet | A | ✓ | ✓ | 9 | 129 | 32 | 0 / 0 (0) |
| ex06-scheduler-subtle | sonnet | B | ✓ | ✓ | 10 | 150 | 47 | 0 / 0 (0) |
| ex07-routes-rare | haiku | A | ✓ | ✓ | 13 | 209 | 68 | 0 / 0 (0) |
| ex07-routes-rare | haiku | B | ✓ | ✓ | 20 | 408 | 61 | 7 / 0 (1) |
| ex07-routes-rare | sonnet | A | ✓ | ✓ | 10 | 169 | 48 | 0 / 0 (0) |
| ex07-routes-rare | sonnet | B | ✓ | ✓ | 12 | 265 | 73 | 0 / 0 (0) |
| ex08-routes-subtle | haiku | A | ✓ | ✓ | 12 | 217 | 80 | 0 / 0 (0) |
| ex08-routes-subtle | haiku | B | ✓ | ✓ | 32 | 1297 | 371 | 5 / 0 (3) |
| ex08-routes-subtle | sonnet | A | ✓ | ✓ | 11 | 175 | 55 | 0 / 0 (0) |
| ex08-routes-subtle | sonnet | B | ✓ | ✓ | 10 | 153 | 45 | 0 / 0 (0) |
| ex09-scheduler-crash | haiku | A | ✓ | ✓ | 11 | 114 | 16 | 0 / 0 (0) |
| ex09-scheduler-crash | haiku | B | ✓ | ✓ | 13 | 159 | 24 | 0 / 0 (0) |
| ex09-scheduler-crash | sonnet | A | ✓ | ✓ | 10 | 121 | 11 | 0 / 0 (0) |
| ex09-scheduler-crash | sonnet | B | ✓ | ✓ | 10 | 137 | 90 | 0 / 0 (0) |
| ex10-routes-crash | haiku | A | ✓ | ✓ | 12 | 118 | 19 | 0 / 0 (0) |
| ex10-routes-crash | haiku | B | ✓ | ✓ | 15 | 220 | 30 | 2 / 0 (1) |
| ex10-routes-crash | sonnet | A | ✓ | ✓ | 10 | 147 | 18 | 0 / 0 (0) |
| ex10-routes-crash | sonnet | B | ✓ | ✓ | 10 | 141 | 24 | 0 / 0 (0) |

## Pre-registered comparisons (B − A, paired)

- **total tokens**: median difference +21508 (95% CI +16340 to +110726), Wilcoxon W+ = 193.0, n = 20, p = 0.000
- **turns**: median difference +1 (95% CI +0 to +3), Wilcoxon W+ = 151.0, n = 18, p = 0.002
- **wall time (s)**: median difference +11 (95% CI +5 to +14), Wilcoxon W+ = 193.0, n = 20, p = 0.000
- **success**: A 20/20, B 19/20; only B: 0, only A: 1, exact McNemar p = 1.000
- **localized**: A 20/20, B 19/20

## Descriptive breakdowns

| group | pairs | success A | success B | median tokens A (k) | median tokens B (k) | median turns A | median turns B |
|---|---|---|---|---|---|---|---|
| category crash | 4 | 4 | 4 | 119 | 150 | 10 | 12 |
| category rare | 8 | 8 | 7 | 159 | 216 | 11 | 12 |
| category subtle | 8 | 8 | 8 | 137 | 211 | 11 | 13 |
| model haiku | 10 | 10 | 9 | 153 | 276 | 12 | 16 |
| model sonnet | 10 | 10 | 10 | 137 | 147 | 10 | 10 |

## pmdb usage in arm B

pmdb or pmdb-record used in 8/20 runs; 39 pmdb calls, 0 pmdb-record calls, 15 failed.

### Error messages printed by pmdb

- 5× `error: expected expression` (e.g. `pmdb /work/report.pmdb -e 'select subtract(_, _) where _' -e 'show $0' | head -100`)
- 4× `error: expected identifier` (e.g. `echo "select spread(5000, [3597610, 33068]) | show \$0" | pmdb /work/report.pmdb`)
- 3× `error: multiple commands should be separated by a newline` (e.g. `pmdb report.pmdb -e 'select /utilization/\.\$result/' -e 'show $0'`)
- 2× `error: expected '…'` (e.g. `echo "select spread(*) from * where true | show \$0" | pmdb /work/report.pmdb`)
- 2× `error: undefined symbol '…'` (e.g. `pmdb report.pmdb -e 'show $0' 2>&1 | head -100`)

## Feedback

- pmdb_usefulness (arm B): median 2, values [1, 2, 2, 2, 2, 3, 3]
- confidence (arm A): median 5.0, values [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
- confidence (arm B): median 5.0, values [4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

### pmdb_problems

- [B haiku ex01-invoicing-rare] Query syntax errors when trying to filter by specific argument values (e.g., 'where code == BIG50' or filtering for specific function results)
- [B haiku ex01-invoicing-rare] Very verbose --show output that required manual grepping to find relevant sections
- [B haiku ex01-invoicing-rare] Documentation states query language is 'under development', suggesting it may be incomplete or unstable
- [B haiku ex01-invoicing-rare] Unclear how to query for return values or results of specific calls
- [B sonnet ex01-invoicing-rare] Did not use it, so can't report concrete runtime problems, but the query language described in the README looked non-trivial to construct correctly on the first try (e.g. remembering variadic binding syntax, where-clause grammar) compared to just reading the ~130-line source file directly.
- [B haiku ex02-invoicing-subtle] Query syntax failures (e.g., 'error: expected identifier') with unhelpful error messages
- [B haiku ex02-invoicing-subtle] Had to guess the correct regex pattern syntax and try multiple times
- [B haiku ex02-invoicing-subtle] Output format didn't clearly show return values; I had to search for snap patterns with /spread\.$result/
- [B haiku ex02-invoicing-subtle] No simple command to 'show all calls to function X' — required learning the query language
- [B haiku ex04-calc-subtle] Trace output is extremely verbose, making it hard to locate relevant sections
- [B haiku ex04-calc-subtle] Query syntax is unclear—'select call(parse, _) where _ > 0' failed with 'error: expected identifier'
- [B haiku ex04-calc-subtle] Tree-formatted output is difficult to scan visually for specific issues
- [B haiku ex04-calc-subtle] No built-in way to filter by specific line numbers or variable names
- [B haiku ex05-scheduler-rare] Query syntax was unintuitive - got 'expected expression' and 'expected identifier' errors when trying reasonable-looking queries
- [B haiku ex05-scheduler-rare] The `-e` flag behavior with multiple commands was unclear; had to debug the syntax
- [B haiku ex05-scheduler-rare] Error messages didn't suggest what the correct syntax should be
- [B haiku ex06-scheduler-subtle] Query syntax was unclear; had to guess the correct form after an initial failure
- [B haiku ex06-scheduler-subtle] Output was extremely verbose, showing all 30 subtract calls across all rooms without easy filtering
- [B haiku ex06-scheduler-subtle] No way to filter results by argument values (e.g., show only calls with window [4800, 5400])
- [B haiku ex06-scheduler-subtle] Documentation didn't include examples of filtering by specific values
- [B haiku ex07-routes-rare] Query error messages were unhelpful ('error: expected identifier' with no context)
- [B haiku ex07-routes-rare] The --show output was extremely verbose, making it hard to find relevant information
- [B haiku ex07-routes-rare] Initial query syntax attempts failed silently or with cryptic errors
- [B haiku ex07-routes-rare] No built-in way to search or filter within the trace output
- [B haiku ex08-routes-subtle] Query syntax was unintuitive - got 'error: expected expression' and 'error: multiple commands should be separated by a newline' with unclear feedback
- [B haiku ex08-routes-subtle] The --show output was extremely verbose and difficult to parse for identifying specific issues
- [B haiku ex08-routes-subtle] Unclear which queries would be useful for finding numeric constants like turn penalties in the trace

### pmdb_wishes

- [B haiku ex01-invoicing-rare] Simpler query syntax with more concrete examples in documentation
- [B haiku ex01-invoicing-rare] Built-in filtering for --show output (like searching for specific values or call results)
- [B haiku ex01-invoicing-rare] Option to display only function return values, not full nested call trees
- [B haiku ex01-invoicing-rare] Better error messages explaining why a query failed
- [B sonnet ex01-invoicing-rare] A quicker 'diff mode' that, given two traces (or a trace and expected values), automatically highlights the first call whose return value diverges from an expectation, instead of requiring the user to hand-write a select query
- [B sonnet ex01-invoicing-rare] Example queries in the README tailored to common debugging patterns (e.g. 'find calls where result differs from a prior call with same inputs') to reduce the learning curve
- [B haiku ex02-invoicing-subtle] Better error messages explaining query syntax when it fails
- [B haiku ex02-invoicing-subtle] A simpler 'trace function X' command that doesn't require query language knowledge
- [B haiku ex02-invoicing-subtle] Side-by-side display of call arguments and return values
- [B haiku ex02-invoicing-subtle] Ability to set breakpoints or highlight anomalies (e.g., when return value is suspiciously close to expected but not exact)
- [B haiku ex04-calc-subtle] Filter traces by function name, return value, or line number to reduce noise
- [B haiku ex04-calc-subtle] Highlight or summarize unexpected values or branches not taken
- [B haiku ex04-calc-subtle] Show only the call stack for a specific line or variable of interest
- [B haiku ex04-calc-subtle] Side-by-side comparison mode showing expected vs actual behavior
- [B haiku ex05-scheduler-rare] Clearer error messages with examples of correct query syntax
- [B haiku ex05-scheduler-rare] A simpler interface for inspecting return values (e.g., 'show return values of utilization calls')
- [B haiku ex05-scheduler-rare] Documentation with more realistic query examples beyond the basic ones shown
- [B haiku ex06-scheduler-subtle] WHERE clause support for filtering by argument values, not just call patterns
- [B haiku ex06-scheduler-subtle] Option to show only result values, not full trace trees
- [B haiku ex06-scheduler-subtle] Better examples in README showing common debugging queries
- [B haiku ex06-scheduler-subtle] Ability to search/filter traces by specific values to find relevant calls faster
- [B haiku ex07-routes-rare] Search/filter capability (like grep on trace output) to find specific function calls
- [B haiku ex07-routes-rare] Better error messages for query syntax with examples of correct syntax
- [B haiku ex07-routes-rare] Option to collapse/expand or summarize parts of the trace
- [B haiku ex07-routes-rare] Ability to show only results for specific functions without full tree traversal
- [B haiku ex08-routes-subtle] Better error messages that explain why a query failed
- [B haiku ex08-routes-subtle] Example queries for common debugging patterns (e.g., filtering by function return values)
- [B haiku ex08-routes-subtle] A simpler way to extract specific numeric values from nested trace data
- [B haiku ex08-routes-subtle] Ability to grep/filter trace output before displaying

### other_wishes

- [A haiku ex01-invoicing-rare] A trace or logging option that shows intermediate values like volume discount rates per line would have made the bug even more obvious without needing manual calculation tracing.
- [A sonnet ex01-invoicing-rare] None needed here; the bug was small enough that reading code plus a diff of outputs was sufficient. For a larger/more opaque codebase, a tool to auto-bisect which input field/order caused a given output diff would have been nice.
- [A sonnet ex02-invoicing-subtle] A quick way to diff per-field/per-row structured output (e.g. JSON diff) rather than plain text diff would have made pinpointing which exact value diverged slightly faster, though it wasn't really necessary here since the file was small.
- [A sonnet ex03-calc-rare] A line-level diff tool output alongside the files would have been convenient (I ran diff manually via Bash), but nothing significant was missing for a codebase this small.
- [A haiku ex04-calc-subtle] A side-by-side diff of actual vs expected output (e.g., showing line 12: got -4, expected -55) would have made the problem even more obvious immediately
- [A sonnet ex06-scheduler-subtle] None needed here — reading the small, well-documented source plus a targeted diff was sufficient; a debugger would have helped confirm the loop trace but wasn't necessary given the code size.
- [A haiku ex07-routes-rare] A graph visualization tool would have made manual path verification faster
- [A haiku ex07-routes-rare] A code comment explaining that the algorithm handles multiple equal-cost paths would have highlighted the tie-breaking logic as a potential issue area
- [A sonnet ex07-routes-rare] A quick way to annotate/log the full set of equal-cost candidate paths found during a Dijkstra run, rather than hand-deriving edge costs and turn penalties to confirm a tie
- [A sonnet ex07-routes-rare] A diff tool that highlights numeric vs. textual differences separately (e.g. flagging 'same total, different path' lines specially) would have shortened the triage step
- [A sonnet ex08-routes-subtle] A way to get per-edge/per-turn cost breakdowns printed by the program itself (e.g. verbose mode) would have made isolating the off-by-one penalty faster than manual arithmetic.
- [A sonnet ex10-routes-crash] None needed here — the traceback from a normal run was sufficient; a debugger would have helped more if the bug had produced incorrect-but-non-crashing output instead of an exception.
- [B haiku ex01-invoicing-rare] A diff tool for comparing traces from expected vs actual runs to highlight divergence points
- [B haiku ex01-invoicing-rare] Quick reference guide showing patterns for debugging common bugs (missing logic, wrong values, etc.)
- [B haiku ex01-invoicing-rare] Ability to set conditional breakpoints or watches on specific values in the trace
- [B sonnet ex01-invoicing-rare] Nothing else was really needed here — the codebase was small enough that reading the source and manually recomputing one line by hand was faster than tooling overhead.
- [B haiku ex02-invoicing-subtle] A linter that flags suspicious patterns like `x += 0` or `return [0] * n` followed by code that should distribute values
- [B haiku ex02-invoicing-subtle] The actual vs expected output diff was more valuable than pmdb — tools that compare program output are more direct for this class of bug
- [B sonnet ex02-invoicing-subtle] None needed here — reading the small codebase and comparing output to expected was sufficient; pmdb's trace-query approach would likely help more on larger codebases or non-deterministic bugs where output diffing doesn't localize the fault so cleanly.
- [B sonnet ex03-calc-rare] None needed here — the codebase was small enough (under 300 lines total) that direct code reading plus running the program was faster than setting up a trace query.
- [B haiku ex04-calc-subtle] Automatic diff output showing which lines produced wrong results
- [B haiku ex04-calc-subtle] A simple test runner that shows 'line X: got Y, expected Z'
- [B haiku ex05-scheduler-rare] A linter that flags unusual variable initializations (initializing a counter to 1 instead of 0 is suspicious)
- [B haiku ex05-scheduler-rare] The ability to quickly inject print/debug statements without rerunning pmdb-record
- [B sonnet ex05-scheduler-rare] None needed here — diffing output against expected_output.txt plus reading the small, well-documented source files was sufficient to localize and confirm the bug quickly.
- [B haiku ex06-scheduler-subtle] A minimal test script or REPL to quickly test subtract() with specific inputs
- [B haiku ex06-scheduler-subtle] Inline algorithm documentation in the code explaining edge cases of interval logic
- [B haiku ex07-routes-rare] For this bug, a simple code review of planner.py would have been faster than debugging—the `<=` vs `<` issue in Dijkstra's algorithm is a well-known problem
- [B sonnet ex07-routes-rare] A way to directly ask 'are there multiple optimal paths for this query' would have shortcut the manual cost-recomputation step, but plain Python scripting was fast enough here that no extra tool was really needed.
- [B haiku ex08-routes-subtle] The test cases and expected outputs should be shown upfront to focus debugging effort immediately
- [B haiku ex08-routes-subtle] A way to add assertions or logging to the code would speed up hypothesis testing
- [B haiku ex08-routes-subtle] A built-in test harness that shows pass/fail for each test case after each run
- [B sonnet ex08-routes-subtle] A small script or REPL helper to quickly recompute path costs/headings from input.json would have made the manual verification faster, though in this case manual arithmetic was fast enough.
- [B sonnet ex08-routes-subtle] I never actually invoked pmdb despite it being set up with a pre-recorded trace; a nudge or example showing how a query like 'turn_penalty(_, _) where ...' could have directly surfaced the per-call penalty values might have made me use it instead of hand-computing geometry.
- [B sonnet ex09-scheduler-crash] None needed here — a plain Python traceback was sufficient since the bug caused a hard crash with a clear stack trace.
- [B sonnet ex10-routes-crash] Nothing additional needed here — the crash was deterministic and the traceback was self-explanatory, so standard tools (Read + running the script) were enough.

### wasted_effort

- [A haiku ex04-calc-subtle] I read all three source files (lexer.py, parser.py, evaluator.py) without a clear hypothesis first, rather than narrowing to evaluator.py immediately after seeing the logical operator bug. Also did not attempt pdb debugging, which might have been faster for some developers.
- [A haiku ex07-routes-rare] I spent time manually tracing through the graph and calculating path costs to verify both routes had equal duration, which wasn't necessary once I recognized the tie-breaking issue. I could have identified the <= vs < bug immediately by examining the algorithm.
- [A sonnet ex07-routes-rare] Manually computing headings and turn penalties by hand for both routes to verify the tie, instead of just writing a quick script to print path costs or using a debugger to inspect the `best` dict during the search.
- [B haiku ex01-invoicing-rare] Spent significant time exploring whether the < operator was wrong and should be >, even testing that change. Also wasted effort trying to use pmdb's query language with various syntax attempts before just reading --show output manually.
- [B haiku ex02-invoicing-subtle] Exploring pmdb didn't lead to finding the bug. My pmdb queries showed the function was being called and what it returned, but I could have just read the 14 lines of code directly and found the bug instantly.
- [B sonnet ex03-calc-rare] I never actually used pmdb or inspected report.pmdb; reading all four source files and the input/expected output was enough to spot the bug, so the recorded trace wasn't needed.
- [B haiku ex04-calc-subtle] Initial attempt to query pmdb failed with a syntax error. The verbose trace output required significant scrolling to find the relevant section. I could have skipped pmdb and found the bug faster by directly reading the evaluator code.
- [B haiku ex05-scheduler-rare] Attempting to use pmdb queries with `-e` flags to examine the utilization function's behavior. The query syntax was confusing and errors weren't helpful, but reading the code directly would have been faster anyway.
- [B sonnet ex05-scheduler-rare] Reading availability.py's full pmdb documentation and recording infrastructure was unnecessary since the bug was findable by direct code review and a quick output diff, without needing to consult the pre-recorded trace at all.
- [B haiku ex06-scheduler-subtle] Spending time with pmdb was somewhat unproductive. I tried several query formats before getting the syntax right, and the output was very verbose across all rooms/windows, making it hard to isolate the specific case. I could have found the bug faster by just reading and reasoning through the code.
- [B haiku ex07-routes-rare] Several failed pmdb query attempts (like `select fastest_route($0)` which returned 0 results) and navigating the extremely verbose --show output. In retrospect, just reading planner.py and spotting the `<=` vs `<` issue would have been faster.
- [B sonnet ex07-routes-rare] I read the pmdb README in full before deciding not to use it, since the bug was findable faster by direct computation/diffing of outputs than by querying a trace.
- [B haiku ex08-routes-subtle] Spent significant time trying to understand if the heading function had North/South swapped by manually tracing routes and turn calculations. Also attempted to use pmdb but had difficulties with query syntax that prevented quick analysis.
- [B haiku ex09-scheduler-crash] Reading the pmdb documentation—the standard Python traceback was sufficient to locate and understand the bug, making pmdb unnecessary for this task.
- [B sonnet ex09-scheduler-crash] Reading pmdb's README in full before discovering the bug was reproducible with a plain traceback, making the pmdb investigation unnecessary overhead.
- [B haiku ex10-routes-crash] I attempted to use pmdb to analyze the trace after seeing the stack trace, but this didn't help. The stack trace was sufficient to identify and fix the bug in seconds.
- [B sonnet ex10-routes-crash] Reading the pmdb README in full before confirming the bug was reproducible by simply running the program; it turned out unnecessary since the plain traceback was sufficient.

### key_step

- [A haiku ex01-invoicing-rare] Using diff to narrow the problem from 'output doesn't match' to a specific 1-cent difference in one line item, which immediately suggested a rounding or discount calculation issue.
- [A sonnet ex01-invoicing-rare] Running `diff` between actual and expected output pinpointed the exact order/line/field that was wrong, which let me work backward through line_subtotal to the volume_discount_rate function and notice the off-by-one against the tier threshold.
- [A haiku ex02-invoicing-subtle] The diff output showing that SKU-657 and SKU-957 in order 3-0 had net values off by 1-2 cents pointed to a rounding/distribution issue, which led me directly to the spread function where I spotted the literal typo: shares[i] += 0 instead of += 1.
- [A sonnet ex02-invoicing-subtle] Spotting the line `shares[i] += 0` inside spread() while reading the code — it was visually odd next to `leftover -= 1`, and the docstring explicitly says leftover cents should go to the first lines, making the off-by-zero obvious on inspection.
- [A haiku ex03-calc-rare] Noticing that line 118 in evaluator.py checked `!= -1` for the OR operator's right operand when it should check `!= 0` to match the truthiness convention used elsewhere in the code.
- [A sonnet ex03-calc-rare] Noticing that the `&&` branch compared the right operand to `!= 0` while the `||` branch compared it to `!= -1`, an obviously asymmetric and incorrect comparison.
- [A haiku ex04-calc-subtle] Spotting the asymmetry: && correctly evaluates tree[3] (right side) on line 116, but || incorrectly evaluates tree[2] (left side) on line 118, when both should evaluate tree[3] for the right operand.
- [A sonnet ex04-calc-subtle] Visually reading the short-circuit evaluation code for `&&` and `||` side by side and noticing `||` reused the index for the left operand instead of the right operand.
- [A haiku ex05-scheduler-rare] The diff output showing only one line differed (21% vs 22%) immediately narrowed the problem to the utilization calculation function rather than something more complex.
- [A sonnet ex05-scheduler-rare] Diffing actual vs expected output showed the bug was isolated to exactly one value (R1 busy %), which pointed directly at utilization() and let me spot the covered = 1 initialization by inspection.
- [A haiku ex06-scheduler-subtle] Using diff to compare outputs showed two specific discrepancies: R2 Monday and R3 Thursday both showed free slots ending at 18:00 instead of 17:30. Looking at the bookings for those times (both starting at 17:30 but extending past 18:00) revealed the pattern.
- [A sonnet ex06-scheduler-subtle] Diffing actual vs expected output pinpointed the exact two lines that were wrong, which let me focus directly on subtract() instead of auditing the whole codebase.
- [A haiku ex07-routes-rare] The diff output showing both paths took the same time (5m32s) but used different streets revealed this was a tie-breaking problem, directing me to examine the shortest-path algorithm's comparison operators.
- [A sonnet ex07-routes-rare] Noticing that the mismatched line had an identical total time (5m32s) to the expected output but a different path, which reframed the bug from 'wrong shortest path' to 'ambiguous tie-breaking among equal-cost paths'.
- [A haiku ex08-routes-subtle] Calculating expected turn penalties by subtracting base street times from expected totals: B2→A0 expected 35s penalties but got 36s, and D2→A0 expected 60s but got 62s. This pattern pointed directly to left turn penalty being 1 second too high.
- [A sonnet ex08-routes-subtle] Noticing that the printed route descriptions were identical between actual and expected output but the times differed by small amounts, then manually tracing headings and turn penalties for each trip and finding the time gap equaled exactly 1 second per left turn.
- [A haiku ex09-scheduler-crash] The traceback showing 'IndexError: list index out of range' on the exact line 'busy[i][0] < end' with the condition 'i <= len(busy)' immediately revealed the off-by-one error.
- [A sonnet ex09-scheduler-crash] The traceback from running the program showed the exact line (availability.py:33, `while i <= len(busy) and busy[i][0] < end`) where the index went out of range, immediately revealing the off-by-one condition.
- [A haiku ex10-routes-crash] Running the program and reading the traceback, which showed IndexError at the exact line and revealed the logic error: accessing an out-of-bounds index when merging consecutive streets.
- [A sonnet ex10-routes-crash] Running `python3 main.py input.json` directly, which produced an uncaught IndexError traceback pinpointing the exact line and reason for failure, rather than a silent mismatch.
- [B haiku ex01-invoicing-rare] Running a local Python test of spread(1, [40, 12]) to see it produces [1, 0], which is exactly the 1-cent reduction needed, showing that amount should be 1 not 5000.
- [B sonnet ex01-invoicing-rare] Noticing that the only quantity in input.json equal to a volume-discount tier threshold (10) was exactly the line that diverged, then checking volume_discount_rate and seeing it used strict '>' instead of '>=' against a value documented as a 'minimum quantity'.
- [B haiku ex02-invoicing-subtle] Reading the spread() function code directly and noticing line 88 adds 0 instead of 1, which contradicts the docstring 'giving leftover cents to the first lines'.
- [B sonnet ex02-invoicing-subtle] Diffing actual vs expected output line-by-line showed the discrepancy was isolated to the one order using a fixed coupon, narrowing the search to spread() immediately.
- [B haiku ex03-calc-rare] Noticing that evaluator.py line 118 checked `!= -1` for the || operator while line 116 checked `!= 0` for &&, revealing a typo that broke logical OR evaluation.
- [B sonnet ex03-calc-rare] Manually evaluating the boolean expression on line 3 of input.txt (`60 > -7 && -7 >= 1 || !(3 == 3)`) by hand and noticing the evaluator's `||` branch compared the right operand to -1 instead of 0, breaking the 'anything nonzero is true' convention stated in the evaluator's own module docstring.
- [B haiku ex04-calc-subtle] Seeing in the pmdb trace that the || operator was calling evaluate(tree[2]) twice instead of evaluating tree[3], which showed the right operand was never being evaluated.
- [B sonnet ex04-calc-subtle] Comparing the '&&' and '||' branches side by side in evaluator.py and noticing '||' referenced tree[2] instead of tree[3].
- [B haiku ex05-scheduler-rare] Seeing the discrepancy in the output (22% vs 21%) and then reading the utilization function's initialization of `covered = 1` instead of `covered = 0`.
- [B sonnet ex05-scheduler-rare] Diffing actual vs expected output narrowed the bug to a single numeric field (utilization percentage), which pointed directly at the utilization() function rather than requiring a trace through the whole call graph.
- [B haiku ex06-scheduler-subtle] Seeing that the actual output had 'free thu 08:00 - thu 18:00' while expected had 'free thu 08:00 - thu 17:30' for room R3 immediately pointed to a bug in free slot calculation. This narrow symptom made the logic error obvious when reading the subtract function.
- [B sonnet ex06-scheduler-subtle] Running the program and diffing against expected_output.txt to localize the bug to a single wrong line, then manually tracing subtract() with the actual minute values for that one case.
- [B haiku ex07-routes-rare] Finding the `reconstruct.$result` in the pmdb trace showing the actual path taken, then realizing both the actual and expected paths had identical 332-second costs, which indicated the algorithm wasn't handling equal-cost paths deterministically.
- [B sonnet ex07-routes-rare] Computing the cost of both candidate routes by hand (via a small script) and finding they were exactly tied, which shifted the hypothesis from 'wrong shortest path' to 'nondeterministic tie-breaking in the relaxation condition'.
- [B haiku ex08-routes-subtle] Writing a comprehensive test script that exhaustively tried all combinations of right_turn and left_turn penalty values and checked which ones matched the expected outputs. This revealed that right=10, left=25 was the solution.
- [B sonnet ex08-routes-subtle] Noticing that the time discrepancy on each mismatched route (1s and 2s) exactly equaled the number of left turns on that route, which pointed directly at the left-turn constant in turn_penalty being off by one second.
- [B haiku ex09-scheduler-crash] The error traceback itself, which pinpointed the exact line and exception type (IndexError at busy[i] access).
- [B sonnet ex09-scheduler-crash] Running `python3 main.py input.json` and reading the resulting Python traceback, which pinpointed the exact line and the out-of-range index.
- [B haiku ex10-routes-crash] Running the program and reading the stack trace, which showed the exact line (52) and the problematic array access (directions[-2][1]).
- [B sonnet ex10-routes-crash] The traceback from directly running the program showed the exact failing line (directions[-2][1] + 1) and the IndexError, immediately revealing that -2 was out of range and almost certainly should have been -1.
