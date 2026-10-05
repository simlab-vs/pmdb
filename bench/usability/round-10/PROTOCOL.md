# Round 10 (quick, exploratory): the trace and its format only, no pmdb (protocol)

Written before any run. Changes after the first run are listed at the end.

## Question

Rounds 7–9 gave arm B pmdb, a skill and a trace, and required their use. The trace decided the
post-mortems, but agents paid for learning and working around the tool. At the user's request,
round 10 asks: **what if agents only get the trace and a terse description of its binary format,
always included in the prompt, and write whatever reader they want?** It is a quick look, not a
powered comparison.

## Design

- **Arm C only:** 18 runs. Arms A and B are round 9's, run 2 days earlier with the same
  scenarios, models, limits and sandbox.
- **Scenarios:** three of round 7's (unchanged), where the pmdb arms did worst in rounds 7–9:
  card-ledger-queue, payroll-postmortem and refund-postmortem.
- **Models:** Haiku, Sonnet and Opus 5.5, with 2 repetitions each.
- **Parallelism:** 8 runs at a time. The plan is drawn with seed 10.
- **Arm C gets** round 9's prompt, with the tools paragraph replaced by:
  - one paragraph: a trace has been recorded, no tool to read it is installed, write your own
    reader if you need one, and use the trace;
  - the format, `harness/schema.txt` (358 words).
- **Arm C doesn't get** a skill, pmdb, or the recorder package. The trace is recorded as in round
  9, by `pmdb-record` at `9003d9d` (format 1.1, with the value table), mounted for recording
  only. The sandbox also hides the store copies of the repository.
- **Checking the format text:** a reader written only from `schema.txt` parsed a
  payroll-postmortem trace to the last byte (149,986 calls) and matched `recorder.load`'s values.

## Measurements

Per scenario and model, as in round 9:
- successes out of 2;
- median tokens and turns;
- the time and tokens spent writing the reader;
- the errors made in it.

These are compared with round 9's arms A and B in the same cells. A qualitative look at the
readers and at how agents analysed the trace.

## Changes after the start

None yet.
