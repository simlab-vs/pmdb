# Round 7: post-mortem scenarios, pmdb required: report

60 runs: 5 hand-designed post-mortem scenarios × 2 arms × 3 models (Haiku, Sonnet, Opus 5.5) ×
2 repetitions.
- **The scenarios:** the failing run can't be replayed (private data, changed external state,
  the clock, a consumed queue).
- **Arm A** gets the code, the production log and the issue.
- **Arm B** also gets pmdb, the skill and a trace of the failing run, and **is required to use
  pmdb**, as decided by the user.
- **The setup:** pmdb and the skill at `9e888ce`, with `export`, `...` among patterns and the new
  warnings. The protocol is in [../PROTOCOL.md](../PROTOCOL.md); `runs.jsonl`, `behaviour.md` and
  `transcripts.tar.xz` are next to this file.

## Results

Successes out of 2, with median tokens and turns:

| scenario | model | A | B |
|---|---|---|---|
| card-ledger-queue | haiku | 1/2, 789k, 23 | 0/2, 4167k, 74 |
| card-ledger-queue | sonnet | 2/2, 582k, 27 | 2/2, 1026k, 31 |
| card-ledger-queue | opus | 2/2, 85k, 7 | 2/2, 209k, 13 |
| payroll-postmortem | haiku | 0/2, 5075k, 73 | **2/2, 2510k, 52** |
| payroll-postmortem | sonnet | 2/2, 1715k, 42 | 2/2, 1612k, 43 |
| payroll-postmortem | opus | 2/2, 128k, 9 | 2/2, 296k, 14 |
| points-expiry | haiku | 2/2, 506k, 21 | 1/2, 1311k, 34 |
| points-expiry | sonnet | 2/2, 303k, 15 | 2/2, 878k, 31 |
| points-expiry | opus | 2/2, 64k, 6 | 2/2, 185k, 11 |
| refund-postmortem | haiku | 0/2, 544k, 27 | 1/2, 2893k, 59 |
| refund-postmortem | sonnet | 0/2, 786k, 30 | **2/2**, 2519k, 52 |
| refund-postmortem | opus | 0/2, 108k, 8 | **2/2**, 378k, 17 |
| stock-allocation | haiku | 2/2, 1149k, 36 | 2/2, 1209k, 40 |
| stock-allocation | sonnet | 2/2, 796k, 29 | 2/2, 864k, 29 |
| stock-allocation | opus | 2/2, 114k, 9 | 2/2, 108k, 8 |

Overall: A 21/30, B 26/30.
- **Haiku:** A 5/10, B 6/10.
- **Sonnet:** A 8/10, B 10/10.
- **Opus:** A 8/10, B 10/10.

B's median tokens are about twice A's for every model.

## Findings

- **pmdb decides post-mortems where the trace carries data no other source has.**
  - refund-postmortem replicated round 6: A 0/6, B 5/6. The winning pattern was to export the
    calls and group them by refund in Python, keeping each refund's last status.
  - In payroll-postmortem the recorded data put real contract gaps in front of every model. It
    turned Haiku from 0/2 at 5.1M tokens into 2/2 at 2.5M tokens: the **first efficiency gain**
    measured in this study.
  - Several Sonnet runs rebuilt the deleted input from recorded arguments and re-ran the job.
- **Where the log and code suffice, the trace adds cost.** In stock-allocation and points-expiry
  the issue or log leads to the defect, and the trace only confirmed it, at 1.0–3× the tokens.
  Haiku was misled by the trace in card-ledger-queue: a difference in call counts pointed at the
  scenario's red herring.
- **The analysis happens in Python, not in pmdb.** Every success went through `export` and
  Python. Agents rebuilt program objects from exported values (`Txn(**json)`, `Message(...)`)
  and ran them through the program's own code. Four Haiku runs reached for a Python API that
  doesn't exist (`pmdb.load(...).calls.where(lambda …)`).
- **The avoidable share of B's extra cost is large.** By the transcript analysis's estimate, it
  is 25–45% for Sonnet and Haiku and about 10% for Opus:
  - loading the trace again on every invocation;
  - failed queries;
  - oversized `show` output;
  - discovering the export's layout;
  - many one-off Python scripts.
- **pmdb errors by cause:**
  - dotted method names without slashes, about 13 (`select Ledger.apply_refund(...)`), which the
    parser rejects before the name warning can help;
  - pipes in the heredoc;
  - `show <file>`;
  - variables reused across invocations;
  - ordering strings (dates);
  - clause order.

  The name and shape warnings fixed their query in one turn every time they fired, about 4 times.
- **What agents wanted:**
  - count, sum and group-by (nearly every run);
  - joins between selections;
  - calls inside or around a call;
  - "first" and "last" by order;
  - differences between selections;
  - object identity;
  - sets and tuple-keyed dicts as values;
  - ordering of strings;
  - rebuilding the program's input from a trace.

## Consequences

1. **The post-mortem setting is where pmdb pays off,** and where its cost can be cut most.
2. **Most of the missing features are plain Python.** Aggregation, joins, ordering, differences
   and objects come for free in a Python library over the trace, and agents already finish
   there. A Python API, with navigation of the call tree and values as Python objects, is the
   next step to evaluate, as proposed to the user.
3. **Quick fixes to the current tool:**
   - accept `Class.method` without slashes;
   - say when a pipe ended the input early;
   - document the export's schema with a sample line in the skill.
