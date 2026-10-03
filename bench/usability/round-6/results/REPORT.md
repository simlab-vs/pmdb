# Round 6: hand-designed scenarios for runtime evidence (exploratory)

Six scenarios were **designed to need runtime evidence**, so this round can show where pmdb
helps, not how much it helps in general (see [../README.md](../README.md) and each scenario's
`notes.md`). Each scenario ran once per model (Haiku, Sonnet, Opus 5.5) and arm, giving 36 runs.
- **Arm A** gets the program, the issue and whatever the scenario provides.
- **Arm B** also gets pmdb, the skill, and `/work/report.pmdb`, a trace of the reported run.

The setup:
- Claude Code 2.1.283, without network;
- pmdb and the skill at `2777a5d`;
- harness `harness/run_scenarios.py`; per-run records in `runs.jsonl`; transcripts in
  `transcripts.tar.xz`.

## Results

✓/✗ is the oracle's verdict on the final sources; tokens are the total processed.

| scenario | model | A | B |
|---|---|---|---|
| billing-needle | haiku | ✓ 1539k, 45 turns | ✗ 5720k, 81 turns |
| billing-needle | sonnet | ✓ 553k, 20 turns | ✓ 1496k, 39 turns |
| billing-needle | opus | ✓ 90k, 8 turns | ✓ 116k, 8 turns |
| bundle-memo | haiku | ✓ 4954k, 77 turns | ✓ 3520k, 71 turns |
| bundle-memo | sonnet | ✓ 876k, 26 turns | ✓ 860k, 25 turns |
| bundle-memo | opus | ✓ 64k, 5 turns | ✓ 94k, 6 turns |
| hashseed-intermittent | haiku | ✓ 589k, 24 turns | ✗ 1865k, 37 turns |
| hashseed-intermittent | sonnet | ✓ 448k, 18 turns | ✓ 546k, 22 turns |
| hashseed-intermittent | opus | ✓ 53k, 6 turns | ✓ 125k, 9 turns |
| refund-postmortem | haiku | ✗ 623k, 25 turns | ✗ 4808k, 76 turns |
| refund-postmortem | sonnet | ✗ 861k, 32 turns | **✓** 2176k, 46 turns |
| refund-postmortem | opus | ✗ 248k, 12 turns | **✓** 387k, 16 turns |
| shared-tiers | haiku | ✓ 980k, 27 turns | ✓ 1048k, 31 turns |
| shared-tiers | sonnet | ✓ 636k, 22 turns | ✓ 960k, 27 turns |
| shared-tiers | opus | ✓ 62k, 7 turns | ✓ 65k, 5 turns |
| slow-planner | haiku | ✗ timed out (30 min) | ✗ 3312k, 59 turns |
| slow-planner | sonnet | ✓ 651k, 21 turns | ✓ 1552k, 33 turns |
| slow-planner | opus | ✓ 65k, 6 turns | ✓ 219k, 11 turns |

Success: A 14/18, B 14/18.

## Findings

- **Only the post-mortem scenario needed the trace.** In refund-postmortem the failing run's
  input is private: arm A gets the code, the log and the wrong totals. Sonnet and Opus failed
  without the trace and succeeded with it.
  - The decisive fact was the sequence of statuses per refund, which only the recorded run
    contains.
  - Agents found it by exporting the recorded calls (Opus parsed a 330 MB `--export-xml`;
    Sonnet regex-parsed `show` output) and grouping them in Python. So the win comes from the
    data the trace carries; pmdb's queries only selected.
- **The other five scenarios didn't need runtime evidence.** Their input was in `/work` and runs
  were cheap or deterministic, so arm A produced the same evidence with short scripts against
  the program's own modules. Some designs also leaked the cause into the issue (shared-tiers) or
  put the nondeterminism downstream of a deterministic defect (hashseed). With the trace, runs
  usually cost more: learning the skill, failed queries, and very large outputs to parse.
- **Haiku** failed most often with pmdb: misused syntax (pipes in the heredoc, `...` in the
  middle of patterns, `show <file>`), and in billing-needle a coincidence the trace showed.
- **What agents needed and pmdb lacked:**
  - counting, summing and grouping;
  - projecting fields;
  - a compact export of selected calls;
  - `...` after other argument patterns;
  - warnings when a pattern's arguments don't fit any call;
  - keywords such as `load` as field names;
  - comment-only lines in a session.

## Harness problems

- **Some oracles called `patch`, which wasn't on the sandbox's `PATH`.** Every run of
  shared-tiers and hashseed-intermittent was first graded as a failure. All runs were graded
  again (`run_scenarios.py regrade`; the first outcome is kept as `success_before`).
- **The pmdb call counter** also counts commands that merely mention pmdb (e.g. `grep -v pmdb`).

## Consequences

- **pmdb changes after this round** (`0132676`..`5824f91`):
  - `export $N to "file"` (typed JSON Lines);
  - `...` among other argument patterns;
  - a warning when no recorded call has a pattern's argument shape;
  - keywords as property names;
  - comment-only lines;
  - the skill recipes for exporting and for traces you are handed.
- **Round 7 focuses on post-mortem scenarios**, where replaying the failure is impossible for
  several reasons (private data, external state, time, consumed queues), with two runs per cell.
