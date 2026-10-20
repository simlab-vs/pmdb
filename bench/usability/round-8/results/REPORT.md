# Round 8: post-mortem scenarios, pmdb required, Python queries: report

60 runs, the same design as round 7: 5 post-mortem scenarios × 2 arms × 3 models (Haiku, Sonnet,
Opus 5.5) × 2 repetitions.
- **Arm B** must use pmdb on a trace of the failing run.
- **The only change** is that pmdb and the skill are at `c9e9a61`. The skill now leads with the
  Python library over traces (`recorder.load`).
- The protocol is in [../PROTOCOL.md](../PROTOCOL.md). `runs.jsonl`, `behaviour.md` and
  `transcripts.tar.xz` are next to this file.

## Results

Successes out of 2, with median tokens and turns; round 7's arm B for comparison:

| scenario | model | A r8 | B r8 | B r7 |
| card-ledger-queue | haiku | 1/2, 916k, 25 | 1/2, 2753k, 50 | 0/2, 4167k, 74 |
| card-ledger-queue | sonnet | 2/2, 423k, 24 | 2/2, 954k, 30 | 2/2, 1026k, 30 |
| card-ledger-queue | opus | 2/2, 126k, 10 | 2/2, 295k, 14 | 2/2, 209k, 12 |
| payroll-postmortem | haiku | 0/2, 2016k, 44 | 1/2, 5054k, 75 | 2/2, 2510k, 52 |
| payroll-postmortem | sonnet | 2/2, 1376k, 40 | 2/2, 2626k, 50 | 2/2, 1612k, 43 |
| payroll-postmortem | opus | 2/2, 104k, 8 | 2/2, 336k, 14 | 2/2, 296k, 14 |
| points-expiry | haiku | 2/2, 540k, 20 | 2/2, 1296k, 35 | 1/2, 1311k, 34 |
| points-expiry | sonnet | 2/2, 319k, 17 | 2/2, 455k, 19 | 2/2, 878k, 31 |
| points-expiry | opus | 2/2, 71k, 6 | 2/2, 153k, 10 | 2/2, 185k, 11 |
| refund-postmortem | haiku | 0/2, 712k, 28 | 0/2, 3719k, 66 | 1/2, 2893k, 59 |
| refund-postmortem | sonnet | 0/2, 1039k, 33 | 2/2, 2474k, 49 | 2/2, 2519k, 52 |
| refund-postmortem | opus | 0/2, 152k, 8 | 2/2, 399k, 17 | 2/2, 378k, 17 |
| stock-allocation | haiku | 2/2, 1456k, 46 | 2/2, 964k, 32 | 2/2, 1209k, 40 |
| stock-allocation | sonnet | 2/2, 1093k, 36 | 2/2, 670k, 26 | 2/2, 864k, 28 |
| stock-allocation | opus | 2/2, 84k, 7 | 2/2, 190k, 12 | 2/2, 108k, 8 |
r8 haiku A 5 10 1080k pmdb 0 failed 0

**Overall, round 8 against round 7:**

| | round 8 | round 7 |
|---|---|---|
| arm A | 21/30, median 427k tokens | 21/30, 550k |
| arm B | 26/30, median 914k tokens | 26/30, 1164k |

The geometric mean of the per-cell ratio of B's median tokens to A's is **2.07** in round 8 and
2.01 in round 7. Arm A, the control, also used fewer tokens this time, so the drop in B's
absolute tokens is not a gain from the library.

Ratio of B's median tokens to A's, by model:

| model | round 8 | round 7 |
|---|---|---|
| Haiku | 2.55 | 2.52 |
| Sonnet | 1.46 | 1.85 |
| Opus | 2.42 | 2.07 |

pmdb CLI invocations in B fell from 278 to 113, and failed ones from 52 to 35. Almost all of the
remaining failures were Haiku's: 34, mostly pipes inside the heredoc.

## Findings

- **The success rate held, and the cost did not drop.** Only Sonnet's ratio improved
  (points-expiry 878k → 455k, stock-allocation 864k → 670k). Haiku did worse on its two
  post-mortems:
  - payroll-postmortem went from 2/2 to 1/2;
  - refund-postmortem went from 1/2 to 0/2.
- **Agents adopted the library, mostly after a first CLI step.**
  - Almost every run began with `pmdb … show functions`.
  - Opus and Sonnet moved to Python within a few steps; Haiku moved later and kept going back to
    the CLI.
  - Agents used `calls`, `args`, `result`, `first`, `count` and `functions`, and did their own
    grouping with `Counter` and dicts.
  - `group_by` was used once. `show`, `before`/`after` and `path` were essentially unused.
- **The largest avoidable cost was setup, not the library.**
  - The skill says to put the recorder's directory on `PYTHONPATH`, but in the sandbox
    `import recorder` already worked.
  - Agents that searched for the recorder with `find /` picked up a stale copy of this
    repository's source in the read-only `/nix/store`, which has no `load`.
  - This affected 8 runs (mostly Opus). Two Opus runs (card-ledger-queue 1, refund-postmortem
    2) gave up on the library and went back to `export`.
- **Errors from the shapes of values.** Each line gives how many runs hit it.
  - Named tuples are recorded as tables, so they load as dicts, and `.field` failed (5).
  - Sets and other objects load as `Opaque`, and agents didn't know about `unpickle()` (4).
  - `Call.returned` is a property, but `Calls.returned()` is a method (2).
  - `self` is `args[0]` for methods (2).
  - `.first()` can return `None` (2).
  - A tuple loads as a list, so it can't be a dict key (1).
  - `where` silently drops calls whose predicate raises, which hid some of these mistakes.
- **Every script reloads the trace,** 2–42 times per run. On traces of 40+ MB this costs wall
  time rather than tokens. Agents also pasted the same object-rebuilding helpers into each
  one-off script; one Sonnet run wrote 29 scripts.
- **Haiku's failures were reasoning failures, not tool failures.** In each failing post-mortem,
  Haiku never used the trace to check its fix against the reported figures; that check is what
  rescued its one payroll success. Examples:
  - **payroll 2:** it ignored 31 `pay_person` calls with 0 days and edited a constant that has
    no effect in September.
  - **refund 1:** it deduplicated refunds keeping the first event instead of the last, and
    stopped with "€83.07 too high, <0.7% error".
  - **refund 2:** it never grouped by refund, and edited defaults that the configuration file
    overrides.
- **Estimated avoidable share of B's extra cost:**
  - Opus about 15%, mostly the import detours. The rest is replaying the job to verify the fix.
  - Sonnet 25–30%: discovering value shapes, re-pasted helpers, `show` outputs of up to 4.4 MB.
  - Haiku about 50%, of which only about 10 points are tool mechanics; the rest is wrong
    hypotheses.
- **Agents asked for:**
  - aggregation (group, count, sum), though `group_by` and `count` already exist;
  - the recorder's location (`pmdb --python-path`);
  - values as the program's types: attribute access on records, sets, objects;
  - replaying recorded calls through patched code to verify a fix (6 runs).

## Consequences

1. **Fix the setup in the skill.** Tell agents to check `python3 -c 'import recorder'` first, and
   to set `PYTHONPATH` only if that fails. The stale copy in `/nix/store` is an artefact of the
   bench, but users can also have several copies installed.
2. **Make the library's shapes visible in the skill:**
   - a compact table of the API;
   - tables load as dicts and arrays as lists;
   - `self` is `args[0]`;
   - `Opaque.unpickle()`;
   - `Calls.returned()` against `Call.returned`.
3. **Design decisions for the user,** since they touch the uniform encodings:
   - restoring named tuples, tuples and sets on load, or recording them differently;
   - attribute access on tables;
   - whether `where` should report predicates that raised;
   - a replay helper.
4. **The success rate is robust to the change of interface. The cost is not set by the query
   interface but by setup, value shapes and the agent's reasoning.** Verifying a fix against
   the recorded figures is what separated Haiku's successes from its failures.
