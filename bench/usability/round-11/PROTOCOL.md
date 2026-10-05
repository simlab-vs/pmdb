# Round 11 (quick, exploratory): the trace with pmdb's query language, no skill (protocol)

Written before any run. Changes after the first run are listed at the end.

## Question

Round 10 gave agents only the trace and a description of its format, and they did as well as
with pmdb, at a lower cost. At the user's request, round 11 gives the trace and pmdb's
command-line tool with a terse reference to its query language in the prompt. It asks how the
query language compares with writing one's own reader, under the same conditions.

## Design

- **Arm D only:** 18 runs, as round 10.
  - **Scenarios:** card-ledger-queue, payroll-postmortem and refund-postmortem (round 7's,
    unchanged).
  - **Models:** Haiku, Sonnet and Opus 5.5, with 2 repetitions each.
  - **Parallelism:** 8 runs at a time. The plan is drawn with seed 11.
- **Arm D gets** round 10's prompt with the tools paragraph replaced by:
  - one paragraph: pmdb is installed, a trace has been recorded, use pmdb and the trace;
  - the reference, `harness/reference.txt` (344 words): invocation, commands (`select`,
    `show`, `show functions`, `export`, comments), patterns, outcomes, `from`, conditions and
    value shapes.
- **What arm D has:** `/opt/pmdb/bin/pmdb`, built at `137e68d` (release, with host paths
  stripped).
- **What arm D doesn't have:**
  - the skill;
  - the Python recorder package;
  - a description of the trace format.

  The trace is recorded as in round 10, with the recorder mounted for recording only.
- **`export` is included** because it is part of pmdb's commands. Agents of round 7 analysed
  exports in Python, and this keeps that possible.

## Measurements

As round 10, compared with:
- round 10's arm C;
- round 9's arms A and B;
- round 7's arm B (which had the command-line tool and a skill).

Also measured: the number of pmdb commands, failed commands, and the use of `export`.

## Changes after the start

None yet.
