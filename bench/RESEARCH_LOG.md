# Research log

What we set out to learn about pmdb as a debugging tool for coding agents, what we tried, what we
found, and what we decided. Entries are appended in order and are not rewritten afterwards. If a
later finding contradicts an earlier one, add a new entry that says so.

Each entry has: **Context** (why), **What we did**, **Findings**, **Decisions**, and **Open
questions**. Link to protocols, results and commits instead of copying them.

---

## 2026-10-01: How to measure whether pmdb helps

**Context.** pmdb lets agents query recorded traces instead of stepping through a live program.
We want to know when that saves effort compared with an agent on its own, without designing
exercises that favor the tool.

**What we did.** We reviewed prior work and designed a methodology.
- **Prior work:**
  - debug-gym (Microsoft, 2025): pdb hurt on easy tasks and helped on hard ones.
  - DebugBench: runtime information helps with crashes and wrong names, not with logic bugs.
  - Whyline: "why" questions over a trace cut human debugging time about 8×.
  - SWE-bench contamination studies: models can name the buggy file from the issue text alone.

**Decisions (methodology).**
- **Hypotheses by bug class.** pmdb should help with:
  - rare data-dependent calls among many (T1);
  - wrong values carried along call chains (T2);
  - deep recursion (T3);
  - performance and call counts (T4).

  It should not help with bugs visible in the source (T8) or crashes with a clear traceback (T9).
  Those serve as controls.
- **Protect against bias:**
  - choose programs by rule and place bugs mechanically (mutation operators at sites drawn with
    a seed); nobody picks bugs by hand;
  - categorize bugs by measured runtime features after generating them;
  - generate prompts from a template that gives only the symptom;
  - keep the information the same in both arms (same reproduction, uniform instrumentation);
  - calibrate difficulty with a model that is not evaluated;
  - keep a dev set and a test set that is run once;
  - grade with hidden tests;
  - fix the analysis in a protocol before any run.
- **Separating the value of the trace data from the value of the query language** needs a third
  arm: traces exported as XML without pmdb (`pmdb --export-xml` exists since `a9cb57d`).

**Open questions.** Effect sizes are unknown. The exercises are written by the model family under
study, which is a known limitation.

---

## 2026-10-01: Which models, and how to pay for runs

**Context.** We have an OpenRouter key and a Claude Code Pro subscription.

**Decisions.**
- **For claims about efficiency:** pay per token through OpenRouter, pinning the model ID, the
  effort level and the provider. Use Opus 5.5 as the main model, Haiku 4.5 as a weaker second
  model, and Fable 5.1 as a ceiling check on hard categories. Calibrate with Sonnet 5, and use a
  non-Claude model for any judgment that defines categories.
- **The subscription is for development and exploratory work.** Its usage limits interrupt runs,
  and longer runs are interrupted more often, which correlates with the pmdb arm. So an
  interrupted run is redone, never counted as a failure, and subscription runs are never mixed
  with paid runs in one comparison.
- **For round 1 (exploratory)**, the user chose the subscription with Sonnet and Haiku, and a
  small number of runs.

---

## 2026-10-01: Usability study, round 1

**Context.** We wanted feedback on how agents use pmdb and the Python recorder before investing
in a full benchmark. Protocol: [usability/round-1/PROTOCOL.md](usability/round-1/PROTOCOL.md). Report:
[usability/round-1/results/REPORT.md](usability/round-1/results/REPORT.md).

**What we did.**
- **Exercises:** four programs written for the study (invoicing, a calculator language, a room
  scheduler, a route planner). From 237 measured mutants, a fixed rule selected 10 exercises: a
  rare and a subtle silent bug per program, plus two crash controls.
- **Arms:** A has Python and pdb. B adds pmdb, the recorder, `pmdb-record`, the README's
  query-language section, and a trace of the failing run recorded in advance.
- **Setup:** `claude-sonnet-5` and `claude-haiku-4-5`, one run per condition (40 runs). pmdb
  frozen at `a9cb57d`.
- **Sandbox:** bubblewrap with a fresh home directory, nothing from the host, no web tools and
  no subagents.
- **Feedback:** a questionnaire in the same session after each task.

**Findings.**
- **Efficiency:** pmdb made runs costlier and never more successful. Paired B − A medians:
  +21.5k tokens (p < 0.001), +1 turn (p = 0.002) and +11 s. Success was 20/20 without pmdb and
  19/20 with it.
- **The exercises were too easy.** Diffing the actual against the expected output and then
  reading 100–300 lines localized every bug, and crash controls were solved from the traceback.
- **Reading the README costs tokens even when pmdb is not used.** 19 of 20 pmdb-arm runs read it.
  Sonnet never ran pmdb.
- **Haiku used pmdb in 8 of 10 runs and 15 of its 39 calls failed:**
  - literals in argument patterns;
  - `_` used inside where clauses;
  - `f.$result` (needs `/f\.\$result/`);
  - `$0` across separate `-e` invocations;
  - commands piped with `|`.

  Error messages gave no position or example.
- **Agents wanted to see return values next to calls**, examples shaped like debugging tasks,
  filtering for `--show`, and a trace diff.
- **Agents misread the README as lacking features that exist**, such as filtering by argument
  values.
- **When a query worked, it showed the fault directly** (ex04, ex07).
- **The hidden grading caught one fix that overfitted to the reported example** (Haiku, ex01).

**Decisions.**
- **pmdb changes, in priority order:**
  1. results shown next to calls, and `f(...).$result` or `result` in where clauses;
  2. errors with a column, the expected form and an example;
  3. a "debugging recipes" section first in the README;
  4. several commands per `-e`, or a clear error about variables not persisting;
  5. filtering for `--show`;
  6. later, a trace diff.
- **Round 2 needs harder exercises** (larger programs, bugs far from the symptom, outputs that
  don't localize the fault when diffed) and a short quick reference instead of the full README.
- **Re-run round 1's exercises after the pmdb fixes** to isolate their effect on usability. Use
  new exercises for any claim about efficiency.

**Open questions.**
- Would Sonnet use pmdb at all on harder tasks, or with a shorter reference?
- Does a trace recorded in advance matter, or should agents record their own (no agent used
  `pmdb-record`)?
- Did the Python recorder's newer features (objects recorded as tables, `3590cc2`) remove the
  `<object>` placeholders agents saw for closures and `self`?

---

## 2026-10-01: Detailed analysis of round 1's pmdb attempts

**Context.** The round 1 report summarized usability problems. We wanted to know, for each failed
attempt, whether pmdb broke a documented promise, whether the documentation misled, or whether
agents wanted something unsupported, and what pmdb does today.

**What we did.**
- Extracted all 42 pmdb commands (9 runs, all Haiku) from the transcripts
  ([pmdb_attempts.md](usability/round-1/results/pmdb_attempts.md)).
- Re-ran the failing ones and the forms that would have worked, in the agents' sandbox on their
  traces ([pmdb_reproduced.md](usability/round-1/results/pmdb_reproduced.md)). pmdb's sources are
  unchanged since `a9cb57d`, so this is current behavior.
- Classified each problem and wrote [PMDB_FINDINGS.md](usability/round-1/results/PMDB_FINDINGS.md).

**Findings.**
- **No failure was a broken documented promise.** The failures come from three sources:
  - *Documentation that leaves the natural reading open:* how to select a `$result` label;
    double-quoted strings only; `<source>` in `from` never defined; variables live for one
    invocation.
  - *Unsupported features agents reach for first:* literal values in argument patterns,
    `and`/`or`, testing whether a key exists, scoping into a call's subtree.
  - *Misleading errors:* "multiple commands should be separated by a newline" for most parse
    failures, and no positions.
- **Some queries are valid but silently return nothing:**
  - `fastest_route(E0, A0)` binds variables, and the arity doesn't match;
  - `"…\$result/"` in shell double quotes turns into a regex end anchor.
- **`from $0` searches only the observations in `$0`.** It doesn't search the calls made inside
  them or the `$result` snaps next to them, so "results of this call" can't be expressed.
- **The objects question from the previous entry:** `3590cc2` changes nothing by default.
  Objects are recorded as tables only when their class opts in (`__pmdb__` or
  `recorder.register`).
- **The study's own header** (written for the study) named the `<function>.$result` label without
  saying how to select it. That contributed to finding 1.

**Decisions.** Order of pmdb work, as recommended in the findings:
1. results shown with calls, plus a README section of debugging recipes;
2. errors with a position and a suggestion;
3. literal argument patterns and arity hints;
4. where-clause conveniences (single quotes, `and`/`or`, missing keys);
5. `;` separators, no prompts without a terminal, `--show` as a flag, command name `pmdb`;
6. `in` scoping, `--show` filtering, object attributes recorded by default.

Each change should make the corresponding command in `pmdb_attempts.md` succeed, or fail with an
error that names the fix.

**Open questions.** Should result labels keep `$`? It clashes with both shell quoting and regex
anchors.

---

## 2026-10-01: Incorporating round 1's feedback into pmdb

**Context.** The user chose which recommendations from the detailed findings to implement. They
explicitly ruled out adding many heuristic error messages, because those would complicate the code.
Commits `e935b9d`..`8116b20` on `ci`, one feature each, each with tests.

**What changed.**
- **Results with calls** (finding 1): every printed call shows its outcome, as in
  `call f(3) -> 6` or `call g() raised {message: …, type: KeyError}`, in `show` and in
  `--show`. The tree no longer prints the outcome snaps separately, and its prefixes are fixed.
- **Result binding:** `f(x) -> r where …`. The pattern after `->` is a positional pattern (a
  name, `_` or a literal). It only matches calls whose result was recorded, never calls that
  raised.
- **Literal patterns** (finding 2): Booleans, integers, floats, double-quoted strings and `none`,
  positional or named (`f(10, code = "BIG50")`), compared by equality. An integer never equals a
  float, and `true` never equals `1`. Arrays are not supported as literals, since expressions have
  no array literals either.
- **`t.has("k")`** (finding 3), as a method like `len`. A receiver that isn't a table, or a key
  that isn't a string, is a type error.
  - Alternatives considered: an infix keyword (`t has k`), `"k" in t`, and optional selection
    (`t.k?`).
  - The method form needs no new grammar, works for keys that aren't identifiers (`$variant`) and
    for computed keys, and keeps the table on the left.
- **Command line** (findings 5–6):
  - `-e` removed; commands are read from standard input only, one per line, so agents use a
    heredoc;
  - a command continues only after a trailing `\` outside strings and comments;
  - stdout is flushed before errors, so they appear in order;
  - output is coloured only on a terminal;
  - `--show` is a flag usable before or after the traces;
  - the program is named `pmdb`;
  - the leftover-text error now reads `expected end of command, found '…'`.
- **Numeric literals** accept `_` separators, which the lexer already allowed.
- **Driver tests** read their input from files: writing to a pipe that pmdb had stopped reading
  crashed the test process now and then.
- **Documentation:**
  - the README is reorganized for people (quick start, recording, exploring, query guide by
    example, then the reference);
  - [skills/pmdb](../skills/pmdb) is an agent skill: recording, one-heredoc querying, recipes
    and pitfalls;
  - the study's `pmdb-record`, which records a Python program without editing it, is bundled
    with the skill.
- **Not done:** heuristic error messages (arity hints, suggestions for `and`, single quotes) and
  `--depth`, both by the user's decision.

**Findings while doing it.**
- An independent review of the commits confirmed outcome detection, tree printing, the lexing of
  `->` and literals, and `has`.
- It found two bugs in how multi-line input was read, both fixed:
  - a continued line skipped string tracking;
  - a `"` in a comment started a string, so later commands were silently swallowed.
- String literals can't span lines in the lexer. Continuing a command after an unterminated string
  therefore never produced a valid command, so that rule was dropped.

**Decisions.**
- **Round 1's material stays frozen.** `bench/usability/round-1/opt-pmdb/HEADER.md` and the harness
  still describe and use `-e`, which no longer exists, and they build pmdb from the current
  sources.
- **Round 2** should:
  - give agents the skill instead of the README section;
  - build a fresh `/opt/pmdb` with the skill's `pmdb-record`;
  - re-run round 1's exercises to isolate the effect of these changes, plus new, harder
    exercises for any claim about efficiency.

**Open questions.**
- Should `pmdb-record` move into the Python recorder itself (e.g. `python -m recorder`)?
- Does showing results with calls make `select` listings, without source excerpts, worth adding
  back for agents?

---

## 2026-10-02: Round 1's records stay frozen

**Context.** pmdb's command line changed after round 1 (`-e` was removed). Round 1's
description, harness and results under `bench/usability/round-1/` still refer to `-e`.

**Decision.**
- **Round 1's files stay as they are.** A finished experiment's description, harness and
  results are never modified afterwards, because they must show exactly what the agents saw and
  what was measured.
- **They describe pmdb at `a9cb57d`.** Their mentions of `-e` and of the old output are correct
  for that version.
- **Follow-ups go in a new directory.** That includes re-running round 1's exercises with the
  current pmdb, and updated tooling such as an agent header without `-e`, or an `assemble.py`
  matching the README's renamed "Query language" section. They are recorded in this log.
- **Living documentation describes current pmdb.** This means the README,
  `Documentation/Traces.md` (which now describes the `$result`/`$exception` convention) and
  `skills/pmdb`.

---

## 2026-10-02: One directory per experiment, with a shared library

**Context.** The usability study is getting more rounds, which need their own protocols,
harnesses and results without touching round 1.

**Changes.**
- **Layout.** Round 1 moved to `bench/usability/round-1/` unchanged, apart from the path
  `assemble.py` uses to find the repository. Round 2 starts as a copy of round 1's harness,
  programs and `opt-pmdb` in `bench/usability/round-2/`.
- **Shared library.** Code that doesn't depend on an experiment moved to `bench/lib/pmdbbench`:
  the sandbox, the subscription token, transcript parsing, the statistics, the mutation operators
  and the program runner. Every function was moved verbatim, except that `pmdb_errors` now takes
  a transcript path instead of a run identifier.
- **No behaviour change.** Round 1's harness, before and after the change, produced identical
  programs, mutants, exercises, plans, prepared runs, sandbox probes, analyses and transcript
  parses. The only differences in its outputs were the directory names in the printed paths.

---

## 2026-10-02: History rewritten; old commit hashes

**Context.** CI failed on macOS and Windows: the driver tests didn't find `pmdb` on macOS and
timed out on Windows, a Rust test assumed Unix paths, and XML exports lost tabs and line feeds in
attribute values on macOS. Each fix was folded into the commit that introduced the problem, which
changed the hashes of that commit and of every later commit on `ci`.

**Old and new hashes.** The records of round 1 and earlier entries of this log use the old hashes.
- Round 1 used pmdb at `a9cb57d`. That commit is kept as the tag `usability-round-1`.
- Commits mentioned in this log:

| Old | New | Commit |
|---|---|---|
| `a9cb57d` | `314cdb6` | Export traces to XML (now with the XML writer fix) |
| `3590cc2` | `b1331d0` | Let Python types choose how they are recorded |
| `86168c8` | `c6be50c` | Add a recorder for Rust programs (now with the Windows path fix) |
| `3efe55c` | `2475737` | Add end-to-end tests for pmdb (now with the macOS and Windows fixes) |
| `e935b9d` | `9db7dcb` | Name the command pmdb |
| `8116b20` | `1cb6265` | Add an agent skill for debugging with pmdb |

- Commit messages are unchanged, so other commits can be found by message.
- The latest commit has the same files as before the rewrite.

---

## 2026-10-02: Evaluating and revising the agent skill

**Context.** Round 2 gives agents the skill `skills/pmdb` instead of a README, so the skill was
evaluated before the round, on three new Python tasks unrelated to the study's programs (a ledger
with negative amounts, nested bundle pricing with half-cent rounding, text justification with an
off-by-one). Sonnet subagents fixed each bug following either the original skill or the revised
one, and reported every pmdb command and the friction they hit. An independent reviewer checked
every claim of the skill against pmdb. The workspace isn't committed.

**Results.** Every run fixed its bug. With one run per task and version, the revised skill used
about 16% fewer tokens and 20% less time in the first iteration (57k against 68k tokens, 132 s
against 165 s), which is suggestive at best.

**Problems found and fixed in the skill.**
- **Large arguments.** A function taking a whole catalog prints it on every line of `show` and
  `--show` (2 MB here). The skill now has a script, `clip`, that elides the middle of long lines,
  and it advises querying functions with small arguments.
- **Opaque objects.** Class instances, `self` included, can't be queried. The skill now tells
  agents to add `__pmdb__` before recording. That used to make `pmdb-record` recurse forever,
  because it recorded `__pmdb__` itself; it no longer records the methods the recorder calls on
  values.
- **`pmdb-record` gaps.** It didn't record packages' `__init__.py` and made deep recursions fail.
  It needed `PYTHONPATH` even when run from the repository.
- **Undocumented language limits.** The skill now states them. Values of different types never
  compare, even with `==`, and Python mixes `0` and `0.5`. There's no `%`, and integer `/`
  truncates toward zero. There are no sums or folds, no negative indexes, and no string
  operations. Table keys that aren't identifiers (Rust's `$variant`) can't be read. For checks
  beyond the language, it suggests `--export-xml`.
- **Other guidance.** Batching exploratory queries in one heredoc loses all of them after the
  first error. Arguments are recorded as passed, with keywords as named arguments.

**Open questions (pmdb itself, not changed).**
- Should comparisons between integers and floats be allowed, since Python mixes them freely?
- Should pmdb have `%`, sums over arrays, string operations, or a way to read keys that aren't
  identifiers?
- Should `show` abbreviate large arguments itself?
- Should `pmdb-record` record class instances as tables of their fields by default?

---

## 2026-10-02: Round 2 results

**Context.** Round 2 re-ran round 1's exercises with the current pmdb, the agent skill installed as
a Claude Code skill, and otherwise the same protocol (`usability/round-2/`).

**Results.** See `usability/round-2/results/REPORT.md`.
- **Success:** every run in both arms fixed its bug.
- **Cost:** arm B still costs more, by a median of +57k tokens and +2 turns over 20 pairs
  (p < 0.001 and p = 0.022).
- **Sonnet** used pmdb in 2 of 10 runs and debugged by reading.
- **Haiku** invoked the skill in all 10 of its runs, without being told to.
  - Its pmdb error rate stayed about the same: 13 of 41 commands, against 15 of 39 in round 1.
  - The causes changed. There were no errors from the command line or from missing features.
    The errors were misuses that the skill warns against: `show` without a variable, `$1` with
    one `select`, a pipe inside the heredoc, and SQL-like queries.

**Decisions.**
- **Round 3 goes ahead with exercises built to resist reading.** Round 1's exercises can't show
  an efficiency gain, because reading the code is enough.

**Open questions.**
- Should pmdb's parse errors name what was expected? For example, "`show` expects a variable
  such as `$0`", or listing the defined variables when one is undefined.
- Should `show` have a compact form (calls and results, no excerpts) and a limit, since agents
  didn't use the skill's `grep`/`clip` recipes?
- Should the skill point to snapshots for values inside a call?

---

## 2026-10-02: Detailed pmdb findings of round 2

**Context.** As for round 1, every pmdb command of round 2 was classified by cause, and the failing
ones were re-run in the agents' sandboxes:
- `usability/round-2/results/PMDB_FINDINGS.md`;
- `usability/round-2/results/pmdb_reproduced.md`.

**Findings.**
- **A bug: `*` followed by positional patterns matches nothing.** `f(*, _)` and `f(*, _, *)`
  return no matches although the README says `*` matches any number of positional arguments.
  Variadic matching consumes all remaining arguments without backtracking.
- **Most failures are forms the skill warns against.** Haiku used them right after reading it:
  `show query`, `show $1` after a single `select`, and bare names such as `turn_penalty(S, W)`,
  which silently matched 227 calls instead of 12.
- **Suggested fixes for those failures.** Errors that state what is expected or defined, and
  saying when a call pattern names a function absent from the traces.
- **Agents want a compact `show` and a limit.** No agent used the skill's `clip` or `grep`
  recipes.
- **Candidate features:** a `raised e` pattern for calls that raised, mirroring how calls are
  printed; and `==` between values of different types evaluating to false instead of failing.

---

## 2026-10-02: Round 3 abandoned: reading localizes mutants of larger programs too

**Context.** Round 3 (`usability/round-3/`) generated exercises meant to resist reading:
- three programs of 740–1070 lines with aggregated outputs;
- mutation operators modelling natural-looking bugs;
- candidates filtered to silent, rare, deep mutants changing few output lines;
- a read-only Sonnet screen, which could only read the code and the two outputs, to keep the
  ones it couldn't localize.

**Result.** The screen localized all 18 candidates, in 7 to 11 turns each, at most 2.5 minutes
and 235k tokens.
- A diff of the outputs points to a feature, and the code's names lead from there to the
  mutated function.
- A single mechanical change, even one that reads naturally (a removed `+=`, `continue`
  instead of `break`), stays visible to a reader who knows where to look.

**Decision.**
- **No round 3 runs.** The round is abandoned before any run of the study; its setup and screen
  stay as a record.
- **Round 4 uses real bugs.** As the user chose, it sources real bugs from real projects instead
  of mutants.

**Open question.** Is any mechanical single-site mutation hard to localize by reading, given the
expected output?

---

## 2026-10-02: Round 4: real bugs, three models

**Context.** Round 4 (`usability/round-4/`) used real bugs instead of mutants.
- **Mining.** Recent fixes (April–September 2026) were mined mechanically from 9 pure-Python
  projects on GitHub. Every candidate had to be reproducible offline, recordable, and have at
  most 10 failing tests; 19 of 25 passed.
- **Exercises.** 10 bugs from 7 projects were selected, with hard ones first.
- **Models.** Haiku, Sonnet and Opus 5.5, with and without pmdb: 60 runs.
- **Prompt.** It named the failing tests.

**Results** (`usability/round-4/results/REPORT.md`).
- **No efficiency gain for any model.** 29/30 fixed without pmdb, 30/30 with it. B − A: median
  +76k tokens (p = 0.08) and +2 turns (p = 0.36).
- **The screen localized 20 of 22 bugs by reading alone.** The fixed tests state the cause.
- **The models differ much more than the arms.**
  - Opus fixes in about 6 turns and 51k tokens, with one-shot correct edits, and skips pmdb by
    the skill's own advice.
  - Sonnet uses pmdb to confirm hypotheses it already has.
  - Haiku always uses pmdb, fails 22 of its 59 commands, and was misled by routinely caught
    exceptions matched by `raised`.
- **pmdb helped only where tests hung.** In pipx, it was the only runtime evidence.

**pmdb problems found.**
- **Fixed** (`fbe6e19`): the recorder recursed forever when encoding a value called recorded
  code.
- **Not yet fixed:**
  - the recorder breaks some beets fixtures;
  - `raised` matches exceptions that are caught normally, which the skill invites;
  - bare method names silently match nothing;
  - unhelpful messages: a missing file with no name, `show <path>`, empty results;
  - objects are opaque.

**Harness problems.**
- **The network wasn't blocked.** Agents and fixtures used it.
- **pipx was mis-graded offline,** and was graded again with the network.
- **16 parallel runs on 14 cores** inflated wall times.

**Decisions.**
- **Issues instead of tests.** At the user's suggestion, real-bug rounds give the issue text a
  user reported, not the failing tests. The fixed tests are hidden and still grade the fix. The
  agent reproduces the bug; in the pmdb arm it records its own reproduction.
- **Settings where runtime evidence is needed.**
  - Post-mortem runs that can't be replayed.
  - Performance bugs (the user's suggestion): per-call durations in traces enable queries a
    profiler can't answer. Examples: which arguments make a function slow, identical repeated
    calls, and duration growing faster than input size.
- **The sandbox will block the network for agents** and only reach the API.
- **pmdb gets fixes for the problems above,** one commit each.

---

## 2026-10-02: pmdb fixes from round 4's feedback

**Changes** (one commit each, with tests):
- **The recorder no longer records calls made while it encodes values** (`fbe6e19`). A property
  read by `isinstance` made camel's tests recurse forever.
- **Generator and coroutine functions keep their kind when recorded** (`ac2a5cd`). pytest no
  longer skipped beets' generator fixtures, which had broken one bug and given ex01 a trace of
  setup only. Calls inside generators and coroutines now nest under them, and calls made while
  they are suspended don't. Re-recording round 4's two beets bugs now works and records their
  fix functions.
- **New command `show functions`** lists the recorded functions with their call counts
  (`7ee64db`). A parse error after `show` now says what it expects.
- **Warning when a query names no recorded function** (`e174511`). It lists the functions the
  pattern partially matches, e.g. `MusicBrainzPlugin.get_tracks_from_medium` for
  `get_tracks_from_medium`. This is the most common silent miss in rounds 2 and 4.
- **Clearer error messages:**
  - an undefined variable's error lists the defined ones (`2c9e798`);
  - a trace that can't be read is named, with the reason (`c817efe`).
- **Skill** (`6d588f9`):
  - pmdb is a command on `PATH`;
  - `show` takes a variable, and pipes go after the heredoc;
  - `show functions` and the new warning;
  - `raised` also matches exceptions caught along the way;
  - record one test, not a file.

**Not changed, to decide with the user.**
- Matching a bare name against the last component of qualified names: `take` would match
  `Parser.take`.
- Recording dataclasses as tables by default.
- A compact or limited `show` inside pmdb.

---

## 2026-10-03: Round 5: reported issues, no network, no pre-recorded trace

**Context.** Round 5 (`usability/round-5/`) applied the user's methodology change and round 4's
harness fixes:
- **The prompt** is the GitHub issue the fix closes. The project is at the parent commit, and
  the official tests are hidden and grade the fix.
- **Agents have no network.** Claude Code reaches only the API, through a socat relay.
- **Arm B gets no pre-recorded trace.**
- **pipx was excluded at the user's request,** because its tests need the network.
- **The design:** 9 exercises from 5 projects, 3 models, 54 runs.

**Results** (`usability/round-5/results/REPORT.md`).
- **Agents didn't use pmdb when nothing pointed to it.**
  - The skill was invoked in 3 of 27 pmdb-arm runs.
  - pmdb was run in 1 (Haiku). Sonnet and Opus never ran it.
  - Success was A 12/27 against B 13/27, and B − A tokens p = 0.41.
- **Half the exercises can't be solved from the issue.** Four were solved by no run, and one by
  one run. In the cases inspected, agents fixed the reported behaviour, but the hidden tests
  check unstated implementation choices, such as the exact key wrapping a list in camel.
- **Opus is still about 10× cheaper** than Sonnet and Haiku. All models wrote reproduction tests.

**Harness problem fixed during the round.** The interruption check matched `529` in a
transcript's numbers. It discarded a run that reached the turn cap and stopped the runner. Runs
ending at the turn cap are now kept.

**Decisions.**
- **Measure pmdb's value where its use is natural or required,** not only its adoption:
  - a trace that comes with the report (post-mortem);
  - or an arm instructed to use pmdb.
- **Issue-based exercises need a solvability check before selection.**
- **Round 6 explores hand-designed scenarios where runtime evidence is essential,** in
  parallel. They are labelled as designed to favour pmdb: they test where it can help, not how
  much it helps in general.

---

## 2026-10-03: Round 6: hand-designed scenarios (exploratory)

**Context.** At the user's request, six scenarios were built by hand to need runtime evidence
(`usability/round-6/`):
- a needle in a 3,000-account batch;
- a post-mortem with a private input;
- aliasing;
- a wrong memoization key;
- an intermittent failure;
- a 2-minute run.

They test where pmdb can help, not how much. Each ran once per model and arm (36 runs), with the
pmdb arm handed a trace of the reported run.

**Results** (`usability/round-6/results/REPORT.md`).
- **Success was the same in both arms**: 14/18 each.
- **The trace decided only the post-mortem scenario.** There, Sonnet and Opus failed without it
  and succeeded with it. The decisive information was the private input it carried. Agents got
  it out through a 330 MB XML export or by regex-parsing `show`, then grouped it in Python.
- **The other five were solved without pmdb.** Their input was local and runs were cheap, so
  arm A scripted the same evidence. The trace usually added cost.
- **A harness bug:** some oracles needed `patch`, missing from the sandbox, so all runs were
  graded again.

**pmdb changes from this round** (`0132676`..`5824f91`):
- **`export $N to "file"`** writes typed JSON Lines;
- **`...` among other argument patterns;**
- **a warning when no recorded call has a pattern's argument shape;**
- **keywords as property names;**
- **comment-only lines;**
- **skill recipes** for exporting and aggregating, and for traces you are handed.

**Decision.** Round 7 targets the post-mortem setting, where replay is impossible:
- private data;
- external state that has changed;
- time-dependent behaviour;
- a consumed message queue.

It uses two runs per cell and the improved pmdb.

---

## 2026-10-03: Round 7: post-mortem scenarios, pmdb required

**Context.** Round 7 (`usability/round-7/`) used 5 hand-designed post-mortem scenarios: private
data, changed external state, the clock, and a consumed queue.
- **pmdb required.** Arm B *had to* use pmdb on a trace of the failing run, at the user's request:
  adoption was no longer measured.
- **Runs:** 3 models and 2 repetitions: 60 runs.
- **pmdb:** the version with `export` (`9e888ce`).

**Results** (`usability/round-7/results/REPORT.md`).
- **More successes with pmdb:** A 21/30 against B 26/30.
- **Where the trace carried data nothing else had:**
  - refund-postmortem: A 0/6, B 5/6 (Sonnet and Opus 2/2 each);
  - payroll-postmortem: Haiku went from 0/2 at 5.1M tokens to 2/2 at 2.5M. This is the first
    efficiency gain of the study.
- **Elsewhere the trace only confirmed** what the log and code showed, at about twice the tokens.
- **Every success analysed exported calls in Python.** Agents rebuilt program objects from them,
  and Haiku runs reached for a Python API that doesn't exist.
- **Dotted method names without slashes** were the most frequent failed query.

**Decisions.**
- **Post-mortem is pmdb's setting.** The next step is to cut its cost there.
- **Prototype a Python library over traces.** It would give navigation, ordering, aggregation
  and joins as Python, and values as Python objects. This follows the user's question about
  reusing an existing language; prior work (Expositor, TraceQL, Perfetto's SQL, PQL, Daikon) is
  summarized in the discussion that led here.
- **Quick fixes:** `Class.method` without slashes, and the export schema in the skill.

---

## 2026-10-03: Round 8: post-mortem scenarios, Python queries

**Context.** Round 8 (`usability/round-8/`) repeated round 7's design: the same 5 post-mortem
scenarios, with pmdb required in arm B; 60 runs.
- **The change:** pmdb and the skill at `c9e9a61`, where the skill leads with the Python library
  over traces (`recorder.load`).

**Results** (`usability/round-8/results/REPORT.md`).
- **The success rate held:** A 21/30 against B 26/30, the same as round 7.
- **The cost did not drop.** B used 2.07× A's tokens: the geometric mean of the per-cell ratio of
  medians, against 2.01 in round 7.
  - Only Sonnet improved: 1.46× against 1.85×.
  - Haiku lost 2 post-mortem successes.
- **Agents adopted the library.** pmdb CLI calls fell from 278 to 113.
- **The largest avoidable cost was setup.** The skill told agents to put the recorder on
  `PYTHONPATH`, though it was already importable. Searching for it found a stale copy in
  `/nix/store` without `load`. This hit 8 runs, and 2 Opus runs gave up on the library.
- **Next, the shapes of values.** Named tuples load as dicts, sets as `Opaque`, and tuples as
  lists, and `where` silently drops calls whose predicate raises.
- **Haiku's failures were reasoning,** not tooling. It never checked its fix against the
  recorded figures, which is what its one success did.

**Decisions.**
- **Fix the skill:** check `import recorder` before touching `PYTHONPATH`, and document the
  library's value shapes and API compactly.
- **Ask the user** about restoring Python types on load and about a replay helper. Both touch
  the uniform encodings.

---

## 2026-10-03: Round 9: automatic recording, Python API required

**Context.** Following the user's direction, pmdb now records every call of a program's own code
with `sys.monitoring`:
- arguments by parameter name;
- generators and coroutines as one call each;
- threads;
- `recorder.snap` for values the agent wants recorded.

Traces are queried with a Python library of selectors and conditions, including the relations
`caller`, `callee`, `ancestor`, `descendant`, `before` and `after`, and `Q` combinations
(`29a63a1`). Round 9 (`usability/round-9/`) repeated round 7's design with the Python API
required in arm B, a Python-only skill, and no command-line tool installed: 60 runs.

**Results** (`usability/round-9/results/REPORT.md`).
- **Cost fell.** The B/A token ratio was 1.84, against 2.07 in round 8. Opus went from 2.49 to
  1.72, at 10/10.
- **Successes:** B 22/30, against 26/30 in round 8 (p = 0.33), and A 21/30.
- **One failure came from the API:** a silent wrong answer, `c.returned == value` with
  `c.returned` a Boolean.
- **Seven failures were reasoning:** groupings that missed filtered events, decoys, and the
  turn limit.
- **4 Haiku runs skipped the skill** and guessed the API.
- **Agents used names and filters, rarely relations.**
- **The bench exposed scenario data.** A copy of this repository in `/nix/store`, readable in
  the sandbox, holds the scenarios' private data, ground truths and oracles. No run of any round
  read them.

**Decisions.**
- **Fixed without design decisions (`c8cc580`):**
  - the sandbox hides the store copies of the repository;
  - skill notes on `returned`, on recomputing figures from unfiltered calls, and on looping;
  - a faster `ancestor=`;
  - suggestions for unknown attributes.
- **Ask the user** about value shapes, `returned` naming, module selectors, a replay helper and
  marking defaults.
- **The next round's prompt names the skill.**

---

## 2026-10-05: Round 10: the trace and its format only, no pmdb

**Context.** At the user's request, a quick round (`usability/round-10/`) gave agents a trace and
a 358-word description of its binary format in the prompt. There was no pmdb, no skill, and no
recorder package; agents wrote their own readers.
- **Scenarios:** three post-mortems where the pmdb arms did worst (card-ledger-queue,
  payroll-postmortem, refund-postmortem).
- **Runs:** 3 models, 2 repetitions: 18 runs, 8 in parallel.
- **The format text** was checked first: a reader written only from it parsed a trace to the last
  byte.

**Results** (`usability/round-10/results/REPORT.md`).
- **Successes:** 14/18, against B 15, 14 and 10 in rounds 7–9, and A 9/18 in each round.
- **Cost:** a median of 1,359k tokens, the lowest of any arm with a trace on these scenarios
  (round 9's B: 1,738k).
- **First:** Haiku's card-ledger runs succeeded both times, which no arm had done before.
- **The readers:**
  - Opus wrote a 40-line reader in one step and reused it;
  - Sonnet and Haiku wrote readers of 160–330 lines;
  - two Haiku readers needed one fix each;
  - no run was misled by its reader.
- **The four failures are Haiku's,** with the reasoning failures seen before.

**Decisions.**
- **A documented trace format plus Python is the baseline** pmdb's query layer must beat.
- **The format's description is worth shipping with traces.**
- **A powered B-against-C comparison is needed** before drawing conclusions.
