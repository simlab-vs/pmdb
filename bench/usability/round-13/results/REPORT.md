# Round 13: four forms of access to an execution trace, six exercises: report

72 runs: 4 conditions × 6 exercises × 3 models × 1 repetition.
- **Duration:** 26 minutes (17:36–18:02), 36 runs at a time.
- **Completeness:** no run was interrupted or reached the time limit.
- **Design:** the protocol is in [../PROTOCOL.md](../PROTOCOL.md). Conditions are numbered as
  there: 1 baseline (no trace), 2 query language, 3 Python library, 4 format specification.
- **Data:** `runs.jsonl`, `behaviour.md` and `transcripts.tar.xz` are next to this file.

## Results

Each cell: success (✓ or ✗), tokens / tool calls.

| exercise | model | 1. baseline | 2. query language | 3. Python library | 4. format specification |
|---|---|---|---|---|---|
| billing-postmortem | Haiku | ✗ 262k / 16 | ✗ 1,818k / 37 | ✓ 1,561k / 45 | ✗ 897k / 27 |
| billing-postmortem | Sonnet | ✓ 311k / 18 | ✓ 642k / 23 | ✓ 762k / 25 | ✓ 709k / 27 |
| billing-postmortem | Opus | ✓ 82k / 5 | ✓ 105k / 6 | ✓ 87k / 6 | ✓ 110k / 6 |
| card-ledger-queue | Haiku | ✓ 698k / 19 | ✗ 1,726k / 47 | ✗ 1,440k / 37 | ✗ 3,251k / 51 |
| card-ledger-queue | Sonnet | ✓ 373k / 22 | ✓ 898k / 29 | ✓ 524k / 21 | ✓ 1,068k / 35 |
| card-ledger-queue | Opus | ✓ 115k / 7 | ✓ 226k / 12 | ✓ 118k / 8 | ✓ 180k / 9 |
| payroll-postmortem | Haiku | ✓ 1,714k / 45 | ✓ 4,281k / 79 | ✗ 4,975k / 80 | ✗ 3,821k / 59 |
| payroll-postmortem | Sonnet | ✓ 1,354k / 35 | ✓ 1,215k / 31 | ✓ 1,661k / 38 | ✓ 1,289k / 34 |
| payroll-postmortem | Opus | ✓ 134k / 8 | ✓ 211k / 11 | ✓ 118k / 8 | ✓ 244k / 10 |
| points-expiry | Haiku | ✓ 259k / 12 | ✓ 792k / 25 | ✓ 956k / 32 | ✓ 1,545k / 38 |
| points-expiry | Sonnet | ✓ 414k / 17 | ✓ 513k / 20 | ✓ 421k / 17 | ✓ 794k / 26 |
| points-expiry | Opus | ✓ 74k / 6 | ✓ 82k / 6 | ✓ 82k / 6 | ✓ 113k / 7 |
| refund-postmortem | Haiku | ✗ 813k / 29 | ✗ 2,579k / 62 | ✗ 2,331k / 57 | ✗ 1,386k / 29 |
| refund-postmortem | Sonnet | ✗ 1,132k / 31 | ✓ 2,554k / 50 | ✓ 5,450k / 83 | ✓ 3,327k / 63 |
| refund-postmortem | Opus | ✗ 178k / 8 | ✓ 421k / 13 | ✓ 238k / 12 | ✓ 278k / 13 |
| stock-allocation | Haiku | ✓ 1,423k / 43 | ✓ 773k / 28 | ✓ 599k / 23 | ✓ 2,048k / 40 |
| stock-allocation | Sonnet | ✓ 1,475k / 35 | ✓ 655k / 25 | ✓ 456k / 22 | ✓ 774k / 27 |
| stock-allocation | Opus | ✓ 101k / 7 | ✓ 98k / 7 | ✓ 135k / 9 | ✓ 116k / 7 |

Costs are given per model, as the models differ by an order of magnitude.
- **Ratios to the baseline:** each run's tokens divided by the baseline run's for the same
  exercise and model, then the geometric mean over exercises. "All runs" includes failed runs;
  "pairs" only counts exercises where both runs succeeded, so it measures the overhead of using
  the trace when it was not needed.
- **Tokens per success:** all tokens of the condition divided by its successes.

Successes are out of 6 runs per model and condition: 6 exercises × 1 run.

| condition | successes | median tokens | tokens relative to the baseline, all runs | the same, runs where both succeeded (pairs) | tokens per success |
|---|---|---|---|---|---|
| **Haiku** | | | | | |
| 1. baseline | 4/6 | 756k | 1 | 1 | 1,293k |
| 2. query language | 3/6 | 1,772k | 2.47× | 1.61× (3) | 3,990k |
| 3. Python library | 3/6 | 1,500k | 2.33× | 1.25× (2) | 3,954k |
| 4. format specification | 2/6 | 1,796k | 2.83× | 2.93× (2) | 6,474k |
| **Sonnet** | | | | | |
| 1. baseline | 5/6 | 773k | 1 | 1 | 1,012k |
| 2. query language | 6/6 | 776k | 1.33× | 1.20× (5) | 1,079k |
| 3. Python library | 6/6 | 643k | 1.36× | 1.06× (5) | 1,546k |
| 4. format specification | 6/6 | 931k | 1.62× | 1.44× (5) | 1,327k |
| **Opus** | | | | | |
| 1. baseline | 5/6 | 108k | 1 | 1 | 137k |
| 2. query language | 6/6 | 158k | 1.47× | 1.33× (5) | 190k |
| 3. Python library | 6/6 | 118k | 1.11× | 1.07× (5) | 130k |
| 4. format specification | 6/6 | 148k | 1.48× | 1.46× (5) | 173k |

## Findings

- **Sonnet and Opus: with any form of access to the trace, every run succeeded** (36 of 36 in
  round 13). Their only failures were in the baseline, on refund-postmortem.
  - Without the data, Opus identified the mechanism (each status change is re-sent). Its repair
    still counted refunds that were pending at month end, and was €782.29 too high.
  - The existence and handling of such refunds could only be determined from the data.
- **For Sonnet and Opus, the trace costs little.** Relative to the baseline, over all runs:
  - **Opus:** 1.11× with the Python library, about 1.5× with the query language or the format
    specification.
  - **Sonnet:** 1.3–1.6×.

  Counting only exercises that both runs repaired, the figures are 1.07–1.46× for Opus and
  1.06–1.44× for Sonnet.
  - **On individual exercises:** on billing-postmortem, points-expiry and stock-allocation, which
    both models also repaired without the trace, the overhead was often under 1.5×, and in some
    cases below the baseline (stock-allocation, Sonnet: 0.31–0.52×).
- **The forms of access differ little.** With one run per combination, no condition is better at
  success.
  - The Python library was the cheapest for Opus: 1.11× the baseline's tokens over all runs. On
    the exercises that both runs repaired, it was the cheapest for Sonnet and Opus (1.06× and
    1.07×).
  - The format specification was the most expensive for Sonnet (1.62×), and for Opus about as
    expensive as the query language (1.48× and 1.47×). Each agent first writes and debugs its own
    reader.
- **Haiku does not benefit from the trace.** It repaired 4 of 6 exercises in the baseline, but
  3, 3 and 2 of 6 with the query language, the Python library and the format specification. The
  trace costs it 2.3–2.8× the baseline's tokens. With the trace, it spends its effort on
  analyses that lead to decoys, and more often reaches the turn limit.
- **The new exercise, billing-postmortem, did not require the trace.** Sonnet and Opus repaired
  it in every condition, including the baseline. Like points-expiry and stock-allocation, it is
  solvable from the code, the log and the report.
- **One of six exercises is decisive.** Refund-postmortem is the only exercise where the trace
  changed the outcome for Sonnet and Opus. It is decisive because its defect's exact effect
  depends on data shapes (pending, reversed, re-sent refunds) that the agent cannot infer from
  the code.

## Consequences

- **Having the trace matters, and the form of access matters much less.** For capable models
  (Sonnet, Opus), the trace makes the data-dependent exercise solvable, at a modest cost
  elsewhere. All three forms of access achieve this, with the Python library the cheapest for
  Opus, and the self-written reader the most expensive.
- **For a weaker model (Haiku), the trace is a net cost:** more tokens, and no more successes.
- **Five of the six exercises can be solved without runtime data** by Sonnet and Opus. The
  exercise set says little about how often traces are decisive in practice. More exercises of the
  refund kind would be needed to measure that, where the repair depends on data the code doesn't
  reveal.

## Revision

On 2026-10-05, at the user's request:
- the cost summaries pooled across models (medians and ratios over all runs of all models) were
  replaced by per-model figures;
- the section combining rounds 12 and 13 on their three shared exercises was removed, so that the
  report covers round 13's six exercises only.

The per-run data and table are unchanged.
