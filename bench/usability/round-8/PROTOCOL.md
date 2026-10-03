# Round 8: post-mortem scenarios, pmdb required, Python queries (protocol)

Written before any run. Changes after the first run are listed at the end.

## Question

Round 7 found that with the trace of a failing run that can't be replayed, agents fix more bugs
(B 26/30 against A 21/30), but spend about twice the tokens. Every success analysed the calls in
Python after exporting them, and agents asked for aggregation, joins, ordering and navigation.
Round 8 asks: **when the skill leads agents to query the trace in Python (`recorder.load`, commit
`b9808f3`), does the cost of using the trace drop, and does the success rate hold?**

## Design

Identical to round 7 ([../round-7/PROTOCOL.md](../round-7/PROTOCOL.md)):
- the same 5 scenarios (round 7's `scenarios/`, unchanged);
- the same prompts, with arm B *required* to use pmdb and the trace;
- the same models and 2 repetitions: 60 runs;
- the same limits and offline sandbox.

The plan is drawn with seed 8. Arm A is run again as a same-day control.

**The only differences are pmdb and the skill, at `c9e9a61`.**
- The skill presents the Python library over traces as the way to analyse anything beyond a
  selection: navigation, before/after, `group_by`, counts, and values as Python values.
- pmdb's own query language also accepts qualified names (`Ledger.post(...)`), and later
  commands still run when the output is no longer read.

## Measurements and analysis (descriptive)

As round 7, per scenario, model and arm:
- successes out of 2;
- median tokens and turns;
- pmdb and Python-API use.

Round 8's arm B is compared with round 7's arm B, with this round's arm A as a control for drift
between the two rounds. A qualitative analysis covers how agents used the Python API.

## Changes after the start

None yet.
