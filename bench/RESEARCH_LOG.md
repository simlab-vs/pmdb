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
in a full benchmark. Protocol: [usability/PROTOCOL.md](usability/PROTOCOL.md). Report:
[usability/results/REPORT.md](usability/results/REPORT.md).

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
  ([pmdb_attempts.md](usability/results/pmdb_attempts.md)).
- Re-ran the failing ones and the forms that would have worked, in the agents' sandbox on their
  traces ([pmdb_reproduced.md](usability/results/pmdb_reproduced.md)). pmdb's sources are
  unchanged since `a9cb57d`, so this is current behavior.
- Classified each problem and wrote [PMDB_FINDINGS.md](usability/results/PMDB_FINDINGS.md).

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
