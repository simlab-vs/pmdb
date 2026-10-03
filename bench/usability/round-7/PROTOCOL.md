# Round 7: post-mortem scenarios with pmdb required (protocol)

Written before any run. Changes after the first run are listed at the end.

## Question

Round 6 found one setting where the trace decided the outcome: a failure whose input can't be
replayed (`refund-postmortem`). Round 7 asks, in that setting: **when an agent uses pmdb on a
trace of the failing run, does it fix the bug more often, or with less effort, than without the
trace?**

As decided by the user, arm B is *required* to use pmdb. Whether agents choose pmdb on their own
was measured in round 5 (they didn't), and is not measured here.

## Scenarios

Hand-designed, so this is an existence test for the post-mortem setting, not an unbiased
estimate. Each scenario's `notes.md` gives its design and fairness threats.

| scenario | why the run can't be replayed |
|---|---|
| refund-postmortem | private input, deleted after the run (copied unchanged from round 6) |
| payroll-postmortem | private input |
| stock-allocation | external state (a service's snapshot) that has changed since |
| points-expiry | depended on the clock at the time of the run |
| card-ledger-queue | consumed queue messages, gone after the run |

All five scenarios were complete and validated before the runs started.

The agent gets the program in `/work`, the production log, and the issue. The unavailable input
or state stays in the scenario's `private/`. The scenario's `oracle.py` grades the final sources
on hidden inputs.

## Arms

- **A:** Python 3 with pdb.
- **B:** the same, plus pmdb (`/opt/pmdb`), the pmdb skill (user skill; bundled skills denied),
  and `/work/report.pmdb`, a trace of the failing run recorded with the scenario's `record.sh`.
  The prompt ends: "Use pmdb and this trace in your investigation."

The prompt is otherwise identical: the issue, the tools sentence, "There is no network access",
the request for a minimal fix of the root cause, and the `RESULT:` line. After the task, round 5's
questionnaire.

## Runs

- **Models:** `haiku`, `sonnet` and `opus` (Claude Code 2.1.283, subscription).
- **Plan:** every scenario × arm × model, twice, giving 60 runs with 5 scenarios.
- **Order and limits:** run order drawn with seed 7, 8 at a time, at most 80 turns and 30
  minutes.
- **Sandbox:** round 5's: no network except a relay to the API.
- **pmdb and the skill:** at `9e888ce`, with `export`, `...` among patterns, and argument-shape
  warnings.

## Measurements and analysis (descriptive)

Per scenario, model and arm:
- successes out of 2;
- median tokens and turns;
- pmdb commands and failures.

A qualitative analysis of the transcripts covers how the trace was used, what was decisive, and
the effort that didn't contribute.

With 2 runs per cell, the comparisons are descriptive; no test is pre-registered.

## Changes after the start

None yet.
