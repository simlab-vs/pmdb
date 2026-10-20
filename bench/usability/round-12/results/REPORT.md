# Round 12: four forms of access to an execution trace: report

36 runs: 4 conditions × 3 exercises × 3 models × 1 repetition.
- **Duration:** about 25 minutes (17:10–17:35), 24 runs at a time. No run was interrupted.
- **Time limit:** one run reached the 24-minute limit (Haiku, card-ledger-queue, Python library)
  and counts as a failure; its cost is summed over the model's responses.
- **Design:** the protocol is in [../PROTOCOL.md](../PROTOCOL.md).
- **Data:** `runs.jsonl`, `behaviour.md` and `transcripts.tar.xz` are next to this file.

## Results

Each cell: success (✓ or ✗), tokens / tool calls.

| exercise | model | 1. baseline | 2. query language | 3. Python library | 4. format specification |
|---|---|---|---|---|---|
| card-ledger-queue | Haiku | ✓ 1,427k / 32 | ✗ 4,217k / 75 | ✗ 4,831k / 76 (time limit) | ✓ 3,118k / 54 |
| card-ledger-queue | Sonnet | ✓ 421k / 18 | ✓ 912k / 28 | ✓ 1,088k / 35 | ✓ 1,232k / 35 |
| card-ledger-queue | Opus | ✓ 76k / 5 | ✓ 140k / 8 | ✓ 166k / 8 | ✓ 374k / 16 |
| payroll-postmortem | Haiku | ✗ 1,138k / 33 | ✓ 2,379k / 44 | ✗ 4,823k / 75 | ✗ 4,937k / 67 |
| payroll-postmortem | Sonnet | ✓ 878k / 31 | ✓ 1,191k / 35 | ✓ 1,909k / 42 | ✓ 2,469k / 48 |
| payroll-postmortem | Opus | ✓ 145k / 9 | ✓ 147k / 9 | ✓ 173k / 10 | ✓ 165k / 8 |
| refund-postmortem | Haiku | ✗ 582k / 23 | ✗ 3,418k / 78 | ✗ 1,888k / 47 | ✗ 3,097k / 65 |
| refund-postmortem | Sonnet | ✗ 826k / 30 | ✓ 3,032k / 59 | ✓ 2,136k / 50 | ✓ 3,298k / 56 |
| refund-postmortem | Opus | ✗ 271k / 11 | ✓ 223k / 12 | ✓ 127k / 7 | ✓ 300k / 15 |

Costs are given per model, as the models differ by an order of magnitude.
- **Ratios to the baseline:** each run's tokens divided by the baseline run's for the same
  exercise and model, then the geometric mean over exercises. "All runs" includes failed runs;
  "pairs" only counts exercises where both runs succeeded, so it measures the overhead of using
  the trace when it was not needed.
- **Tokens per success:** all tokens of the condition divided by its successes.

Successes are out of 3 runs per model and condition: 3 exercises × 1 run.

| condition | successes | median tokens | tokens relative to the baseline, all runs | the same, runs where both succeeded (pairs) | tokens per success |
|---|---|---|---|---|---|
| **Haiku** | | | | | |
| 1. baseline | 1/3 | 1,138k | 1 | 1 | 3,148k |
| 2. query language | 1/3 | 3,418k | 3.31× | – (0) | 10,013k |
| 3. Python library | 0/3 | 4,823k | 3.60× | – (0) | – |
| 4. format specification | 1/3 | 3,118k | 3.69× | 2.18× (1) | 11,152k |
| **Sonnet** | | | | | |
| 1. baseline | 2/3 | 826k | 1 | 1 | 1,062k |
| 2. query language | 3/3 | 1,191k | 2.21× | 1.72× (2) | 1,712k |
| 3. Python library | 3/3 | 1,909k | 2.44× | 2.37× (2) | 1,711k |
| 4. format specification | 3/3 | 2,469k | 3.20× | 2.87× (2) | 2,333k |
| **Opus** | | | | | |
| 1. baseline | 2/3 | 145k | 1 | 1 | 246k |
| 2. query language | 3/3 | 147k | 1.16× | 1.37× (2) | 170k |
| 3. Python library | 3/3 | 166k | 1.07× | 1.63× (2) | 156k |
| 4. format specification | 3/3 | 300k | 1.84× | 2.38× (2) | 280k |

## Findings

- **The trace decided refund-postmortem again.**
  - The baseline failed it with every model.
  - With any form of access, Sonnet and Opus repaired it.
  - Haiku failed it in all four conditions.
- **On the other two exercises, the trace mainly added cost.** Sonnet and Opus repaired them in
  every condition, at 1.0–4.9× the baseline's tokens.
- **Among the three forms of access, success is indistinguishable** (7, 6 and 7 of 9). Costs
  were ordered query language < Python library < format specification for Sonnet on
  card-ledger-queue and payroll-postmortem (not on refund-postmortem).
  - This reverses the order seen across rounds 10 and 11, where the format specification was the
    cheaper. With one run per cell, neither ordering is established.
- **How the trace was used:**
  - **Query language:** 4–26 pmdb commands per run, and every run exported to JSON Lines and
    analysed in Python.
  - **Python library:** 2–64 scripts per run.
  - **Format specification:** each run wrote its own reader. Opus named its reader module
    `pmdb.py`, which the command counter mistakes for pmdb commands.
- **Haiku is the noisiest model.** It repaired card-ledger-queue in the baseline and with the
  format specification, but not with the query language or the library; payroll only with the
  query language.

## Consequences

- The result of rounds 7–11 holds under identical conditions: having the trace matters, and the
  form of access to it matters much less than the run-to-run variance.
- A larger sample is needed to rank the forms of access. Round 13 doubles the exercises, to six.

## Revision

On 2026-10-05, at the user's request, the cost summaries pooled across models (medians and ratios over all runs of all models) were replaced by per-model figures. The per-run data and table are unchanged.
