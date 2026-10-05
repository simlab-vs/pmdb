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

| condition | successes (Haiku / Sonnet / Opus) | median tokens / tool calls |
|---|---|---|
| 1. baseline | 5/9 (1 / 2 / 2) | 582k / 23 |
| 2. query language | 7/9 (1 / 3 / 3) | 1,191k / 35 |
| 3. Python library | 6/9 (0 / 3 / 3) | 1,888k / 42 |
| 4. format specification | 7/9 (1 / 3 / 3) | 2,469k / 48 |

## Findings

- **The trace decided refund-postmortem again.**
  - The baseline failed it with every model.
  - With any form of access, Sonnet and Opus repaired it.
  - Haiku failed it in all four conditions.
- **On the other two exercises, the trace mainly added cost.** Sonnet and Opus repaired them in
  every condition, at roughly 1.1–4.9× the baseline's tokens.
- **Among the three forms of access, success is indistinguishable** (7, 6 and 7 of 9). Costs
  were ordered query language < Python library < format specification for Sonnet in every
  exercise, and the medians follow that order.
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
