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

## pmdb and the skill

- 2026-10-01: Incorporating round 1's feedback into pmdb
- 2026-10-02: Evaluating and revising the agent skill
- Changes after round 2 (no log entry; see git history): `raised` patterns, variadic patterns
  anywhere, brief output when not on a terminal, clearer documentation of variables and snap
  labels, the skill limited to Python; integer/float value semantics (`09c1c0d`..`c01502c`).

## Open directions

- Exercises where runtime evidence is needed: issue reports instead of failing tests,
  post-mortem runs that can't be replayed, performance bugs (Round 4 entry).
