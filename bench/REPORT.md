# pmdb for coding agents: experiments, changes and learnings (PR #7)

This report summarizes the branch `ci` (PR #7, 30 September – 4 October 2026):
- what changed in pmdb and its recorders;
- the nine rounds of the usability study run with coding agents;
- what we learned.

The details are in [RESEARCH_LOG.md](RESEARCH_LOG.md) (chronological, append-only),
[RESEARCH_INDEX.md](RESEARCH_INDEX.md) (by topic), and each round's `PROTOCOL.md` and
`results/REPORT.md` under [usability/](usability/).

## Summary

- **pmdb is clearly useful when the failing run can't be replayed.** On a post-mortem with
  private data that a trace carried, arms without the trace fixed 0 of 6 runs in every round
  (rounds 7–9). With the trace, they fixed 5 of 6, 4 of 6 and 3 of 6. In round 6, Sonnet and Opus
  fixed it only with the trace.
- **Elsewhere, pmdb hasn't made agents faster.** Where the code, the log and the issue were
  enough, the trace confirmed what agents had already found, at extra cost:
  - with small exercises and real bugs with tests (rounds 1–4), the cost rose and success stayed
    the same;
  - in post-mortem scenarios with pmdb required (rounds 7–9), the median tokens with pmdb were
    1.8–2.1× those without.
- **The interface improved a lot, and that mattered less than expected.** It went from a
  command-line query language, to the same language plus exports to Python, to a Python library
  with relations between calls.
  - The cost of using the trace fell, most for Opus: 2.49× to 1.72× A's tokens from round 8 to
    round 9.
  - Failures that the tool caused nearly disappeared: 1 of 8 failures in round 9.
  - The remaining failures are reasoning failures that more data doesn't fix: the wrong function,
    a decoy, a residual discrepancy accepted.
- **Most exercises didn't need runtime data.** Strong models localize most bugs by reading:
  - mutants of small and larger programs;
  - real bugs whose tests name the cause.

  Only scenarios whose essential input exists only in the trace separated the arms.
- **Large codebases are the next target, and recording now nearly scales to them.**
  - Recording is automatic, with `sys.monitoring`.
  - A table of values cut beets' traces 6× (4.1 GB to 664 MB for 1.9 million calls).
  - File paths, now 2/3 of the trace, and the speed of recording (about 50× slower than the
    unrecorded run) are the next obstacles.

## What changed

### pmdb (Swift)
- **Robustness:**
  - integer overflow and unterminated regexes no longer crash pmdb;
  - unsupported operators are reported;
  - duplicate named arguments are rejected;
  - parent indices are validated;
  - XML traces with several roots are rejected;
  - floats and 64-bit integers are encoded correctly.
- **Query language:**
  - results bound in call patterns (`f(x) -> r`) and calls that raised (`f(x) raised e`);
  - literals in argument patterns;
  - `*`, `**` and `...` anywhere among patterns, with backtracking;
  - qualified names (`Ledger.post(...)`);
  - `t.has("k")`, `any`, `count` and `len`;
  - prefix, logical, bitwise and equality operators, and lambdas;
  - integers of arbitrary precision compared with floats by value, `int` and `bool`, and
    conditions required to be Booleans.
- **Command line:**
  - named `pmdb`, reading commands from standard input only;
  - `--show` as a flag, and `show functions`;
  - `export $N to "file"` as JSON Lines, and `--export-xml`;
  - `--brief` and `--non-brief`, brief by default when not on a terminal;
  - warnings when a pattern names no recorded function, or no call has its argument shape;
  - errors that list the defined variables and name an unreadable trace;
  - commands keep running when the output is closed.
- **Trace format 1.1:**
  - calls with parameter names and definitions;
  - outcomes that refer to their call, so a generator's outcome needn't follow it;
  - a table storing each value other than numbers and short strings once. Format 1.0 traces,
    such as the Rust recorder's, still load.

### Recorders
- **Python, recording:**
  - **`pmdb-record`** now records every call of a program's own code with `sys.monitoring`,
    without modifying files. It also handles test functions (`pmdb-record -m pytest …`),
    generators and coroutines (one call each, from start to finish), threads and `lru_cache`
    misses.
  - **Arguments** are recorded under their parameter names, defaults included.
  - **`recorder.snap(label, value)`** records a value in the running call, and
    `recorder.recording(path)` records a block of code.
  - **Values** are recorded as they were when observed:
    - `None` and Booleans as themselves;
    - lists and tuples as arrays;
    - dicts with string keys and named tuples as tables;
    - other objects pickled, or by `repr`.

    `__pmdb__` and `recorder.register` let classes choose their recording.
  - **Fixes:** calls made while encoding values are no longer recorded, which used to recurse
    forever; generator functions keep their kind; failures inside callbacks never reach the
    program.
- **Python, querying.** `recorder.load` gives a query library:
  - `t.calls(*selectors, **conditions)`, with selectors (names, regexes, predicates, calls, and
    `Q` combined with `&`, `|` and `~`);
  - conditions `where`, `returned`, `raised`, `caller`, `callee`, `ancestor`, `descendant`,
    `before` and `after`;
  - arguments by name (`c["txn"]`), navigation (`caller`, `callees`, `ancestors`, `path`,
    `tree`), snaps;
  - `group_by`, `count_by`, `values`, and set operations;
  - errors naming the call a predicate failed on, and suggestions for unknown attributes.
- **Rust:** a new recorder (`#[pmdb::record]`), recording wide integers as integers.

### The agent skill (`skills/pmdb`)
- The skill was written, evaluated with agents and revised after rounds 2, 4, 6, 8 and 9.
- It is limited to Python, and now covers only the Python API:
  - recording;
  - snaps;
  - selectors and conditions;
  - value shapes;
  - post-mortem advice;
  - pitfalls.
- At the user's direction it describes no fixed workflow.

### Infrastructure
- **CI** on macOS, Linux and Windows (plus Nix), with end-to-end and binary-trace tests: 92 Swift
  tests. Python unit tests (16) cover the monitor, the query library and the value table. CI
  fixes were folded into the commits that caused them; the old hashes are logged.
- **The benchmark:**
  - `bench/lib/pmdbbench`, shared by all rounds: a bubblewrap sandbox, an offline relay that
    reaches only the API, transcript parsing and statistics;
  - one directory per round, with a protocol written before any run;
  - frozen results;
  - a research log and index.

## The experiments

All runs used Claude Code headless in the sandbox. Arm A had Python and pdb; arm B also had pmdb
and the skill. Both arms got the same prompt, except for what it said about pmdb (and, from round 6
on, the trace).

| Round | Exercises | Models | Main result |
|---|---|---|---|
| 1 | 10 mutants of 4 small programs | Haiku, Sonnet | B cost +21.5k tokens (p < 0.001), success 19/20 against 20/20; Haiku failed 15 of 39 pmdb commands; the exercises were too easy |
| 2 | round 1's, with the skill | Haiku, Sonnet | still +57k tokens; the errors became misuses the skill warns against; Sonnet barely used pmdb |
| 3 | mutants of 3 larger programs | — | abandoned: a reading screen localized all 18 candidates |
| 4 | 10 real bugs, failing tests named | + Opus 5.5 | no gain (A 29/30, B 30/30); the tests give the cause away; models differ more than arms |
| 5 | 9 real bugs, issue text only, offline | 3 models | pmdb used in 1 of 27 runs without a trace; half the exercises unsolvable from the issue |
| 6 | 6 hand-designed scenarios | 3 models | 14/18 in each arm; the trace decided only the post-mortem |
| 7 | 5 post-mortem scenarios, pmdb required, 2 runs per cell | 3 models | B 26/30, A 21/30; refund A 0/6, B 5/6; Haiku payroll 0/2 at 5.1M tokens to 2/2 at 2.5M; B about 2× tokens |
| 8 | round 7's, skill leads with the Python library | 3 models | unchanged success (B 26/30); B/A 2.07; setup and value shapes were most of the avoidable cost |
| 9 | round 7's, automatic recording, Python API required | 3 models | B/A 1.84 (Opus 1.72); B 22/30 (p = 0.33 against 26/30); one failure from an API trap |

**Rounds 7–9** used the same scenarios, so they can be compared. Each cell gives successes out of 2 and
the median tokens (A: without pmdb; B: with pmdb, required):

| scenario | model | A, round 9 | B, round 7 | B, round 8 | B, round 9 |
|---|---|---|---|---|---|
| refund-postmortem | Sonnet | 0/2, 1.2M | 2/2, 2.5M | 2/2, 2.5M | 1/2, 3.2M |
| refund-postmortem | Opus | 0/2, 194k | 2/2, 378k | 2/2, 399k | 2/2, 299k |
| payroll-postmortem | Haiku | 0/2, 3.8M | 2/2, 2.5M | 1/2, 5.1M | 0/2, 3.3M |
| card-ledger-queue | Opus | 2/2, 119k | 2/2, 209k | 2/2, 295k | 2/2, 190k |
| stock-allocation | Sonnet | 2/2, 809k | 2/2, 864k | 2/2, 670k | 2/2, 564k |

## What we learned

### About pmdb's value
1. **Runtime evidence helps when it's the only evidence.** The scenarios pmdb decided were the
   ones whose input or state existed only in the trace:
   - private exports;
   - a consumed queue;
   - hanging tests in round 4.

   Where agents could rerun the program cheaply, prints and reruns were as good as a trace.
2. **Agents use the trace to confirm hypotheses, not to form them.** Every model read the code,
   formed a hypothesis, and then queried. The failures happened at the hypothesis step:
   - grouping a function that never saw the filtered events;
   - following a decoy;
   - patching part of a discrepancy;
   - accepting a residual difference.

   A better query interface doesn't help with those.
3. **Fixed overhead dominates the token ratio for strong models.** For Opus, using the trace
   added roughly 40–120k tokens per scenario: the skill, loading the trace, a few queries. Its
   baseline was 70–190k. So the ratio stays near 2× even when the overhead is small in absolute
   terms. For B to cost less than A, the trace has to replace work agents do anyway: reading
   code, rebuilding inputs, rerunning.
4. **Models differ more than arms.**
   - **Opus** fixes most bugs in 6–10 steps without pmdb.
   - **Haiku's** failures are wrong hypotheses, and more data sometimes misled it.
   - **Sonnet** is where a tool can make a difference.
5. **Agents analyze in Python.** From round 6 on, every success that used a trace finished its
   analysis in Python. Agents exported calls, rebuilt the program's objects and ran the program's
   own code. That led to the Python library.
   - Of the library, agents used names, filters, counts and navigation.
   - They rarely used the relations or `Q`.
   - The most requested missing feature is replay: running recorded calls through patched code to
     check a fix.
6. **Differential analysis is niche.** A ranking of the fields that separate failing calls from
   succeeding ones was checked against all 90 runs with traces from rounds 7–9.
   - It needs calls labelled as failing, which only one scenario's issue provided.
   - It would plausibly have changed 2 of 16 failures.
   - What decided successful runs was simpler:
     - checking a rule against the data;
     - the distinct values of a result over the run;
     - comparing one call with its twin.

### About the usability of the tool
- **Errors moved over the rounds:**
  - **round 1:** missing features and misleading messages;
  - **round 2:** misuses that the documentation warns against;
  - **round 8:** setup (`PYTHONPATH`) and the shapes of loaded values;
  - **round 9:** silent traps: `c.returned == value`, where `returned` is a Boolean.
- **Errors that name the fix work.** These fixed the next query almost every time:
  - the warning about unrecorded functions;
  - the `KeyError` listing a call's parameters;
  - the `QueryError` naming the call a predicate failed on.
- **Silent wrong answers are the dangerous failures.** For example:
  - a filter that matches nothing;
  - a predicate that drops the calls it fails on;
  - a negated relation.
- **Agents skip documentation when the prompt names the API.** 4 of 10 Haiku runs never loaded
  the skill in round 9, and guessed imports instead.

### About the methodology
- **Mutants and real bugs with tests are solved by reading.**
  - A screen that only reads localized all of round 3's mutants and 20 of 22 of round 4's bugs.
  - Real unit tests call the buggy function almost directly. Their traces are tiny: 44–4,875
    calls.
- **Optional tools aren't used without a reason.** In round 5, with no trace handed over, pmdb
  was run once in 27 runs. Requiring it measures value but also charges its overhead where it
  isn't needed.
- **Two runs per cell can't detect moderate effects.** 26/30 against 22/30 has p = 0.33, and
  medians of two runs swing 2× between rounds. Rounds 8 and 9 also changed several things at
  once.
- **Harness problems found and fixed:**
  - network access in round 4;
  - offline grading of tests that needed the network;
  - a missing `patch` in the sandbox;
  - an interruption check matching `529` inside transcripts;
  - run directories that couldn't be deleted;
  - a lost executable bit.
- **The sandbox exposed scenario data.** It mounted the read-only `/nix/store`, which held a copy
  of this repository with every scenario's private inputs, ground truths and oracles.
  - No run in any round read them; three listed the paths, and one said it wouldn't read them.
  - The sandbox now hides these copies.

## Open questions and next steps

**Decisions for the user:**
- **Value shapes on load:**
  - named tuples load as dicts, sets as `Opaque`, unpicklable objects as `repr` strings;
  - whether to rebuild the program's types when possible.
- **Naming:** whether to rename the Boolean `returned` / `raised` of calls, or the value
  condition (`result=`).
- **Small features:**
  - a replay helper;
  - selectors by module;
  - marking defaulted arguments.
- **A string table** for file paths, function names and parameter names. It would cut the
  1.9-million-call beets trace from about 700 MB to about 200 MB.

**Engineering:**
- recording speed: encoding arguments, mostly pickling `self` again on every call, is the cost;
- loading speed for traces of millions of calls.

**The next experiments: large codebases.**
- **Bugs from large pure-Python projects** (beets, sphinx, pylint, pip, poetry and others),
  reproduced end to end rather than by a unit test.
- **Selected by how far the cause is from the symptom:** the fixed function many calls away from
  where the symptom shows, and not greppable from the issue.
- **More runs per cell** (5–6) and fewer cells, focused on Sonnet and Haiku, with one change per
  round.

## Where things are

| What | Where |
|---|---|
| research log and index | [RESEARCH_LOG.md](RESEARCH_LOG.md), [RESEARCH_INDEX.md](RESEARCH_INDEX.md) |
| rounds (protocol, harness, results, transcripts) | [usability/round-1](usability/round-1/) … [usability/round-9](usability/round-9/) |
| shared harness code | [lib/pmdbbench](lib/pmdbbench/) |
| the agent skill | [../skills/pmdb](../skills/pmdb/) |
| the Python recorder and query library | [../Python/recorder](../Python/recorder/) |
