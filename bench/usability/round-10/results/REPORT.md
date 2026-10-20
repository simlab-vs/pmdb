# Round 10 (quick, exploratory): the trace and its format only, no pmdb: report

18 runs in arm C: three of round 7's post-mortem scenarios × Haiku, Sonnet and Opus 5.5 × 2
repetitions, 8 at a time.
- **What arm C got:** the trace, a 358-word description of its binary format
  ([../harness/schema.txt](../harness/schema.txt)) in the prompt, and the instruction to use the
  trace.
- **What it didn't get:** pmdb, a skill, or the recorder package.
- **Comparisons:** arms A and B of rounds 7–9 on the same scenarios. The protocol is in
  [../PROTOCOL.md](../PROTOCOL.md).

## Results

Successes out of 2, with median tokens and turns:

| scenario | model | A r9 | B r9 | **C r10** | B r8 | B r7 |
|---|---|---|---|---|---|---|
| card-ledger-queue | haiku | 1/2, 738k, 21 | 0/2, 4812k, 81 | **2/2, 1968k, 39** | 1/2, 2753k, 50 | 0/2, 4167k, 74 |
| card-ledger-queue | sonnet | 2/2, 747k, 28 | 1/2, 2001k, 44 | **2/2, 1351k, 38** | 2/2, 954k, 30 | 2/2, 1026k, 30 |
| card-ledger-queue | opus | 2/2, 119k, 9 | 2/2, 190k, 12 | **2/2, 191k, 10** | 2/2, 295k, 14 | 2/2, 209k, 12 |
| payroll-postmortem | haiku | 0/2, 3758k, 66 | 0/2, 3346k, 54 | **0/2, 3928k, 66** | 1/2, 5054k, 75 | 2/2, 2510k, 52 |
| payroll-postmortem | sonnet | 2/2, 938k, 33 | 2/2, 1424k, 36 | **2/2, 1309k, 36** | 2/2, 2626k, 50 | 2/2, 1612k, 43 |
| payroll-postmortem | opus | 2/2, 143k, 10 | 2/2, 179k, 10 | **2/2, 175k, 10** | 2/2, 336k, 14 | 2/2, 296k, 14 |
| refund-postmortem | haiku | 0/2, 449k, 22 | 0/2, 2320k, 58 | **0/2, 2654k, 50** | 0/2, 3719k, 66 | 1/2, 2893k, 59 |
| refund-postmortem | sonnet | 0/2, 1230k, 32 | 1/2, 3226k, 60 | **2/2, 2739k, 52** | 2/2, 2474k, 49 | 2/2, 2519k, 52 |
| refund-postmortem | opus | 0/2, 194k, 10 | 2/2, 299k, 17 | **2/2, 255k, 14** | 2/2, 399k, 17 | 2/2, 378k, 17 |

Over the three scenarios:

| | successes | Haiku / Sonnet / Opus | median tokens |
|---|---|---|---|
| A (rounds 7, 8, 9) | 9/18 each round | 1 / 4 / 4 | 457–581k |
| B, round 7 (command line, export) | 15/18 | 3 / 6 / 6 | 1,461k |
| B, round 8 (Python library) | 14/18 | 2 / 6 / 6 | 1,934k |
| B, round 9 (Python library with relations) | 10/18 | 0 / 4 / 6 | 1,738k |
| **C, round 10 (format only)** | **14/18** | 2 / 6 / 6 | **1,359k** |

## Findings

- **With only the format, agents did as well as with pmdb, and cost less.**
  - **Successes:** 14/18, like round 8's B and one fewer than round 7's.
  - **Cost:** the lowest median of all trace arms on these scenarios.
  - **By cell:** C cost less than round 9's B in 6 of 9 cells, and failed in none where round 9's
    B succeeded.
  - **First:** Haiku's card-ledger runs succeeded in both repetitions, which no arm managed in
    rounds 7–9.

  With 2 runs per cell, these are indications, not measured effects.
- **Writing the reader was cheap and reliable.**
  - **Opus** wrote a 40-line reader in its first step on the trace, the fourth or fifth step of
    the run. It reused it with `exec(open(...))` in later scripts, and never needed a fix.
  - **Sonnet** wrote a reader module of 160–190 lines, in steps 10–21.
  - **Haiku** wrote one of 210–330 lines, from step 4. Two Haiku readers first failed on an
    unknown tag (a skipped byte), and each was fixed in the next step.
  - No run reached a wrong conclusion because of its reader.
- **Agents then analysed the trace in plain Python,** with the data structures they chose:
  - lists of calls, with dicts of parameters;
  - outcomes matched to calls by index;
  - groupings and recomputations of the report's figures.

  There was no API to learn, no import path to find, and no value shape to discover beyond what
  the format states.
- **The four failures are all Haiku's, and are reasoning failures seen before:**
  - **refund:** keeping the first event per refund, and excluding pending refunds;
  - **payroll:** blaming the proration divisor, or the period's end.

  All four read the trace correctly.
- **Opus's workflow didn't change.** It read the code, suspected the cause, and checked it with
  one or two scripts over the trace, at nearly arm A's cost: 175–255k tokens, against 119–194k
  for A.

## Consequences

- **For these agents, the value is in the trace data, not in pmdb's query layer.**
  - A documented format plus Python was as effective as pmdb's command-line tool and Python
    library.
  - It was cheaper than the library of round 9, whose extra cost came from learning the API and
    its traps.
- **The format's description belongs with traces.** Handing an agent a trace with its format,
  rather than a tool, is a strong baseline that any query layer must beat.
- **What pmdb's query layer would have to add:** things a 40-line reader doesn't give. For
  example, scaling to traces that don't fit in memory, or relations and navigation that agents
  can't write as easily themselves.
- **To confirm:** a powered comparison of B against C, with more runs per cell and both arms run
  on the same day.
