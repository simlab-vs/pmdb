# Research index

A map of [RESEARCH_LOG.md](RESEARCH_LOG.md), which is append-only and chronological. Entries are
listed here by topic; their titles are the log's headings.

## Method and infrastructure

- 2026-10-01: How to measure whether pmdb helps
- 2026-10-01: Which models, and how to pay for runs
- 2026-10-02: Round 1's records stay frozen
- 2026-10-02: One directory per experiment, with a shared library
- 2026-10-02: History rewritten; old commit hashes

## Experiments

| Round | Exercises | Models | Outcome | Entries |
|---|---|---|---|---|
| [1](usability/round-1/) | mutants of 4 small programs | Haiku, Sonnet | no efficiency gain; many query errors | Usability study, round 1; Detailed analysis of round 1's pmdb attempts |
| [2](usability/round-2/) | round 1's, with the skill | Haiku, Sonnet | no gain; errors now misuses the skill covers | Round 2 results; Detailed pmdb findings of round 2 |
| [3](usability/round-3/) | realistic mutants of 3 larger programs | — | abandoned: a reading agent localized every candidate | Round 3 abandoned |
| [4](usability/round-4/) | 10 real bugs, failing tests given | Haiku, Sonnet, Opus 5.5 | no gain; tests give the cause away; models differ more than arms | Round 4: real bugs, three models |
| [5](usability/round-5/) | 9 real bugs, issue text only, no network | Haiku, Sonnet, Opus 5.5 | pmdb almost never used without a trace; half the exercises unsolvable from the issue | Round 5: reported issues, no network, no pre-recorded trace |
| [6](usability/round-6/) | 6 hand-designed scenarios needing runtime evidence (exploratory) | Haiku, Sonnet, Opus 5.5 | only the post-mortem scenario needed the trace (Sonnet, Opus fixed it only with pmdb) | Round 6: hand-designed scenarios (exploratory) |
| [7](usability/round-7/) | 5 post-mortem scenarios, pmdb required, 2 runs per cell | Haiku, Sonnet, Opus 5.5 | B 26/30 vs A 21/30; refund A 0/6 vs B 5/6; first efficiency gain (Haiku payroll); analysis happens in Python | Round 7: post-mortem scenarios, pmdb required |
| [8](usability/round-8/) | round 7's, skill leads with the Python library | Haiku, Sonnet, Opus 5.5 | success unchanged (B 26/30); cost still ~2× A; setup (PYTHONPATH) and value shapes dominate the avoidable cost | Round 8: post-mortem scenarios, Python queries |
| [9](usability/round-9/) | round 7's; automatic recording; Python query library with relations required | Haiku, Sonnet, Opus 5.5 | B/A tokens 1.84 (Opus 1.72, was 2.49); B 22/30 (n.s.); 1 failure from a silent API trap; store copy of the repo exposed scenario data (unused, now hidden) | Round 9: automatic recording, Python API required |
| [10](usability/round-10/) | 3 of round 7's post-mortems; trace + 358-word format description only, no pmdb (quick) | Haiku, Sonnet, Opus 5.5 | C 14/18 (B: 15, 14, 10 in rounds 7–9; A 9/18) at the lowest median tokens; readers cheap (Opus: 40 lines, one step); failures are Haiku reasoning | Round 10: the trace and its format only, no pmdb |
| [11](usability/round-11/) | round 10's 3 post-mortems; trace + pmdb CLI with a 344-word query-language reference, no skill (quick) | Haiku, Sonnet, Opus 5.5 | D 13/18 (C 14/18), median 1,572k tokens; Sonnet+Opus 12/12, Haiku 1/6; every run exported to Python | Round 11: the trace with pmdb's query language, no skill |
| [12](usability/round-12/) | 3 post-mortems × 4 conditions (baseline, query language, Python library, format spec; references in the prompt, no skill), 1 run per cell, same day | Haiku, Sonnet, Opus 5.5 | 5/9, 7/9, 6/9, 7/9; trace decides refund; forms of access indistinguishable at this sample size | Round 12: four forms of access to a trace, side by side |

## pmdb and the skill

- 2026-10-01: Incorporating round 1's feedback into pmdb
- 2026-10-02: Evaluating and revising the agent skill
- 2026-10-02: pmdb fixes from round 4's feedback
- pmdb changes after round 6: export, `...` among patterns, argument-shape warnings (Round 6 entry)
- Changes after round 2 (no log entry; see git history): `raised` patterns, variadic patterns
  anywhere, brief output when not on a terminal, clearer documentation of variables and snap
  labels, the skill limited to Python; integer/float value semantics (`09c1c0d`..`c01502c`).

## Open directions

- A Python library over traces (navigation, ordering, aggregation, joins, values as objects), after round 7.
- Debugging failures of added preconditions in large applications (user's suggestion): needs navigation, ordering, contrast between failing and normal calls.

- Exercises where runtime evidence is needed: issue reports instead of failing tests,
  post-mortem runs that can't be replayed, performance bugs (Round 4 entry).
