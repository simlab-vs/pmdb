# Round 9: post-mortem scenarios, automatic recording, Python API required: report

60 runs, the same design as rounds 7 and 8: 5 post-mortem scenarios × 2 arms × 3 models (Haiku,
Sonnet, Opus 5.5) × 2 repetitions.
- **Arm B** must use pmdb's Python API (the package `recorder`) on a trace of the failing run.
- **The trace** is recorded by the new `pmdb-record` (`sys.monitoring`, with arguments by
  parameter name).
- **The skill** covers only the Python query library of selectors, conditions and relations
  (`0d8bd1b`). The pmdb command-line tool isn't installed.
- The protocol is in [../PROTOCOL.md](../PROTOCOL.md). `runs.jsonl`, `behaviour.md` and
  `transcripts.tar.xz` are next to this file.

## Results

Successes out of 2, with median tokens and turns; arm B of rounds 8 and 7 for comparison:

| scenario | model | A r9 | B r9 | B r8 | B r7 |
|---|---|---|---|---|---|
| card-ledger-queue | haiku | 1/2, 738k, 21 | 0/2, 4812k, 81 | 1/2, 2753k, 50 | 0/2, 4167k, 74 |
| card-ledger-queue | sonnet | 2/2, 747k, 28 | 1/2, 2001k, 44 | 2/2, 954k, 30 | 2/2, 1026k, 30 |
| card-ledger-queue | opus | 2/2, 119k, 9 | 2/2, 190k, 12 | 2/2, 295k, 14 | 2/2, 209k, 12 |
| payroll-postmortem | haiku | 0/2, 3758k, 66 | 0/2, 3346k, 54 | 1/2, 5054k, 75 | 2/2, 2510k, 52 |
| payroll-postmortem | sonnet | 2/2, 938k, 33 | 2/2, 1424k, 36 | 2/2, 2626k, 50 | 2/2, 1612k, 43 |
| payroll-postmortem | opus | 2/2, 143k, 10 | 2/2, 179k, 10 | 2/2, 336k, 14 | 2/2, 296k, 14 |
| points-expiry | haiku | 2/2, 408k, 19 | 2/2, 811k, 27 | 2/2, 1296k, 35 | 1/2, 1311k, 34 |
| points-expiry | sonnet | 2/2, 303k, 18 | 2/2, 641k, 24 | 2/2, 455k, 19 | 2/2, 878k, 31 |
| points-expiry | opus | 2/2, 68k, 6 | 2/2, 132k, 10 | 2/2, 153k, 10 | 2/2, 185k, 11 |
| refund-postmortem | haiku | 0/2, 449k, 22 | 0/2, 2320k, 58 | 0/2, 3719k, 66 | 1/2, 2893k, 59 |
| refund-postmortem | sonnet | 0/2, 1230k, 32 | 1/2, 3226k, 60 | 2/2, 2474k, 49 | 2/2, 2519k, 52 |
| refund-postmortem | opus | 0/2, 194k, 10 | 2/2, 299k, 17 | 2/2, 399k, 17 | 2/2, 378k, 17 |
| stock-allocation | haiku | 2/2, 1212k, 40 | 2/2, 803k, 28 | 2/2, 964k, 32 | 2/2, 1209k, 40 |
| stock-allocation | sonnet | 2/2, 809k, 30 | 2/2, 564k, 24 | 2/2, 670k, 26 | 2/2, 864k, 28 |
| stock-allocation | opus | 2/2, 82k, 7 | 2/2, 204k, 12 | 2/2, 190k, 12 | 2/2, 108k, 8 |

Overall, with the geometric mean over cells of the ratio of B's median tokens to A's:

| | round 9 | round 8 | round 7 |
|---|---|---|---|
| arm A | 21/30 | 21/30 | 21/30 |
| arm B | 22/30 | 26/30 | 26/30 |
| B/A tokens, all cells | **1.84** | 2.07 | 2.01 |
| Haiku (A, B, ratio) | 5, 4, 2.09 | 5, 6, 2.29 | 5, 6, 2.07 |
| Sonnet | 8, 8, 1.74 | 8, 10, 1.55 | 8, 10, 1.76 |
| Opus | 8, 10, **1.72** | 8, 10, 2.49 | 8, 10, 2.22 |

The fall in B's successes, from 26/30 to 22/30, is within the noise of 2 runs per cell (Fisher's
exact test, p = 0.33).

## Findings

- **The cost of using the trace fell, most for Opus.** Opus fixed every scenario at 1.72× A's
  tokens, against 2.49× in round 8, with about 3 more steps than A, all before its first edit.
  Every cell of Opus's arm B was cheaper than in round 8 except stock-allocation (204k against
  190k). Refund-postmortem stayed decisive for Opus and Sonnet: A 0/4, B 3/4.
- **The library was adopted, with a narrow core:**
  - arguments by name (`c["x"]`) in 26 of 30 runs; the other 4 never loaded the skill;
  - `where`, `returned=`, `count_by`, `params`, `callees()` and `unpickle()` in 7 to 12 runs
    each;
  - the relations rarely: `caller=` 3 runs, `ancestor=` 3, `before=` 1, `Q` 1, `descendant=` and
    `after=` none;
  - snaps and re-recording none.

  16 runs replayed recorded inputs through the program's code.
- **One failure was caused by the API, through a silent wrong answer.**
  - Sonnet card-ledger 1 compared `c.returned == "resend"`, which is always false, because
    `c.returned` is a Boolean while the condition `returned=` compares the value. It concluded
    the deduplication was innocent.
  - The other Sonnet run made the same mistake, noticed the impossible count, and fixed it.
- **The other 7 failures were reasoning failures**, the same kinds as in rounds 7 and 8:
  - **refund** (Sonnet 1, Haiku 2): grouping the calls of a function that never sees the failed
    events, which a filter removes upstream. Two runs ended exactly €83.07 short and stopped.
  - **payroll** (Haiku 2): a partial fix, and the known decoy.
  - **card-ledger** (Haiku 2): the turn limit, inside the parking decoy; one of these runs never
    loaded the skill.
- **4 of 10 Haiku runs never loaded the skill** (0 in round 8). They started by guessing imports
  (`Replay`, `Tracer`), probably because the prompt now names "the package `recorder`". Two of
  them failed.
- **Errors:** about 45 failed calls came from the API or from value shapes, and the next step
  fixed almost all of them.
  - The `KeyError` listing a call's parameters fixed every wrong parameter name at once.
  - Shape errors persisted: named tuples load as dicts, sets as `Opaque`, unpicklable objects as
    `repr` strings.
  - Predicates that raised no longer misled anyone: they stop the query now.
  - **Silent wrong answers:**
    - `c.returned == value`;
    - substring tests on unqualified names;
    - `c.index` used as a list position;
    - `caller=c.caller` when `caller=c` was meant.
  - A per-call loop of `t.calls(…, ancestor=c)` over 150,000 calls hit a timeout.
- **Agents asked for:**
  - replaying recorded calls through patched code, and rebuilding named tuples (14 runs);
  - predictable shapes;
  - sums and diffs of counters;
  - the `returned` / `result` distinction;
  - selecting by module;
  - fewer silent empty results.
- **The bench exposed the scenarios' private inputs.** A copy of this repository, made when its
  flake was evaluated, sits in the read-only `/nix/store` that the sandbox mounts. It contains
  every scenario's private data, ground truths and oracles.
  - Three round 9 runs listed these paths in `find /` output; one said it would not read them.
  - No tool call of any run in rounds 2 to 9 read them.
  - The only store files read were the old recorder's sources, by two Opus runs of round 8, as
    reported there.

  The results stand; the sandbox now hides these copies (`c8cc580`).

## Consequences

1. **The Python API with relations lowered the cost of using the trace,** clearly for Opus.
   Successes didn't change measurably.
2. **Fixed without design decisions (`c8cc580`):**
   - the skill says `c.returned` is a Boolean;
   - it advises recomputing the report's figures from calls that see all the inputs;
   - it advises looping with `c.descendants()` rather than `t.calls`;
   - `ancestor=` is answered from the selected calls' subtrees;
   - unknown attributes suggest close names;
   - the package has a docstring;
   - the sandbox hides the store copies of the repository.
3. **For the user to decide:**
   - the shapes of named tuples, sets and unpicklable objects;
   - renaming the Boolean `returned` / `raised`, or naming the value condition `result=`;
   - selectors by module;
   - a replay helper, the most requested feature two rounds running;
   - marking defaulted arguments.
4. **The prompt for arm B should name the skill, not just the package,** so that agents read it
   before guessing the API.
