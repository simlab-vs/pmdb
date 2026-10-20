# Round 9: post-mortem scenarios, automatic recording, Python API required (protocol)

Written before any run. Changes after the first run are listed at the end.

## Question

In round 8, agents fixed as many bugs with the trace as in round 7 (B 26/30, A 21/30), but used
about twice arm A's tokens. Most of the avoidable cost came from:
- setup (`PYTHONPATH`);
- the shapes of loaded values;
- one-off analysis code.

Following the user's direction, round 9 replaces both the recording and the query interface:
- **Automatic recording.** Every call of the program's own code is recorded with
  `sys.monitoring`, with arguments by parameter name, generators and coroutines as one call,
  and `recorder.snap` for values the agent wants recorded.
- **A query library** of selectors and conditions that expresses relations between calls
  directly, e.g. `t.calls("post", caller=Q("close_month", where=…))`.

Round 9 asks: **when agents must use this Python API, does the cost of using the trace drop
relative to round 8, and does the success rate hold?**

## Design

Identical to rounds 7 and 8 ([../round-7/PROTOCOL.md](../round-7/PROTOCOL.md)):
- the same 5 scenarios (round 7's `scenarios/`, unchanged);
- the same models and 2 repetitions: 60 runs;
- the same limits, offline sandbox and grading.

The plan is drawn with seed 9. Arm A is run again as a same-day control.

**The differences are in arm B:**
- pmdb and the skill are at `0d8bd1b`. The trace of the reported run is recorded by the new
  `pmdb-record`, which records the same calls as before plus parameter names and definitions.
- The skill covers only the Python API: recording, snaps, selectors, conditions, values, and
  what trips queries up. The pmdb command-line tool and its query language are neither
  described nor installed: `/opt/pmdb/bin` is empty.
- The prompt's last sentence is "Use pmdb's Python API (the package `recorder`) and this trace
  in your investigation." Round 8's was "Use pmdb and this trace in your investigation."

## Measurements and analysis (descriptive)

As round 8, per scenario, model and arm:
- successes out of 2;
- median tokens and turns;
- the ratio of B's median tokens to A's, per cell, with its geometric mean;
- uses of the Python API (`behaviour.py`'s `trace` column).

Round 9's arm B is compared with round 8's (and round 7's) arm B, with this round's arm A as a
control for drift. A qualitative analysis covers:
- which parts of the API agents used (relations, `Q`, snaps, parameter names);
- the errors they hit and whether the error messages led to a fix;
- the remaining avoidable cost.

## Changes after the start

None yet.
