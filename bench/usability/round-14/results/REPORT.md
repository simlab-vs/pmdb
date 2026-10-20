# Round 14: four forms of access to an execution trace, without a defect report: report

72 runs: 4 conditions × 6 exercises × 3 models × 1 repetition.
- **Duration:** 23 minutes (20:02–20:25), 36 runs at a time.
- **Completeness:** no run was interrupted, or reached the time or turn limit.
- **Design:** described in the methodology below, copied from the protocol
  ([../PROTOCOL.md](../PROTOCOL.md)). Conditions are numbered 1 baseline (no trace), 2 query
  language, 3 Python library, 4 format specification.
- **Data:** `runs.jsonl`, `behaviour.md` and `transcripts.tar.xz` are next to this file.

The agents were told only "There may be a bug in the Python program in /work."

## Methodology

### Research question

When an automated coding agent is told only that a program may contain a defect, without any
report of its effect, does it find and repair the defect? How do its success rate and its cost
depend on the form in which a record of a production execution is made available? We compare four
conditions: no record; a query language over the record; a Python library over the record; and a
specification of the record's file format alone.

### Terms

- **Agent:** an instance of Claude Code (an AI coding assistant) running non-interactively. It
  works with a fixed set of tools: running shell commands, and reading, searching and editing
  files.
- **Model:** the language model driving the agent: Claude Haiku 4.5, Claude Sonnet 5 or Claude
  Opus 5.5.
- **Exercise:** a program containing one defect, together with the material available about one
  production execution in which the defect had an effect.
- **Trace:** a file recording one execution of a program. It holds every call of a function
  defined in the program's own source files, in the order the calls started, with:
  - the call's arguments, by parameter name, as they were when the call started;
  - the value it returned or the exception it raised;
  - the call during which it was made.
- **pmdb:** the tool under evaluation. It comprises a recorder that produces traces, a
  command-line program that answers queries in a dedicated query language, and a Python library
  for querying traces.
- **Condition:** the form of access to the trace given to an agent (defined below).
- **Run:** one attempt by one agent, under one condition and with one model, to repair one
  exercise.
- **Oracle:** a program that judges a repaired exercise by executing it on hidden inputs.

### Exercises

Each exercise is a batch job that ran in production and produced incorrect figures, and whose
execution cannot be reproduced because the data it processed is no longer available. The agent
receives:
- the program's source code;
- the job's log and the reports it produced.

**It does not receive the defect report.** Each exercise has one, giving the incorrect figures,
the expected figures and the reason the input cannot be provided, but it is withheld in this
study. The "reported symptom" below is therefore unknown to the agent.

The exercises were designed and written for this study by Claude Opus 5.5. The study uses all six:

| exercise | why the execution cannot be reproduced | reported symptom | class of defect | affected records |
|---|---|---|---|---|
| billing-postmortem | the data extract (customer register, meter readings) was deleted after billing | consumption 77.7 kWh short of the meter data system's total | inconsistent keys across modules | 1 of 3,070 accounts |
| card-ledger-queue | the card processor's queue messages were consumed | debits €808.30 short of the bank's, on 202 cards | incomplete identity key | 280 transactions on 202 cards |
| payroll-postmortem | the private HR export was deleted after payment | salaries €16,904.43 above HR's preview | unchecked invariant on intervals | 9 of about 650 persons |
| points-expiry | the job's behaviour depended on the clock, and it ran across midnight | 273,353 loyalty points expired too early | inconsistent reading of the clock | 1,842 of 4,800 members |
| refund-postmortem | the payment provider's export does not leave the production system | NovaPay refunds €5,027.67 (42%) too high | change in an external data model | 103 of 328 NovaPay refunds |
| stock-allocation | the inventory service's stock levels at the time of the run have since changed | short picks and over-shipped marketplace lines, although every check passed | sign error across modules | 116 of 5,123 order lines |

**Components.** Each exercise consists of:
- a program of 900–1,200 lines of Python in 11 to 18 modules, in a realistic business domain;
- a seeded generator of the private input, and a ground truth;
- the production log and reports, produced by running the program on the private input;
- a defect report (withheld in this study);
- a reference repair;
- an oracle;
- for card-ledger-queue, payroll-postmortem, points-expiry and stock-allocation, one or two
  plausible but incorrect repairs, which the oracle must reject.

A validation script checks, for each exercise, that:
- the original program reproduces the reported symptom;
- the oracle rejects the original program, accepts the reference repair, and rejects the
  incorrect repairs;
- recording a trace leaves the exercise's files unchanged.

**Defects.** Each exercise contains exactly one defect, with these properties:
- the code is correct for the common case;
- a condition present in a minority of the input records, or of the moments of execution, makes
  the program produce incorrect totals;
- the program terminates normally, and its internal consistency checks pass;
- the condition is visible only in the execution, which the trace records and the agent otherwise
  lacks.

The defects make localization by reading costly without making it impossible: the defective code
is documented and appears deliberate, the triggering condition is not apparent from the code, and
the logs report only aggregates. For each exercise:

- **billing-postmortem.**
  - **Mechanism:** readings are merged in order of the account identifier as delivered, but
    grouped by the resolved identifier. An account whose old meter reports under a legacy
    identifier is settled twice, and its second bill overwrites the first.
  - **Repair:** collect each account's readings before settling it.
  - **Plausible alternative causes:** rounding, meter rollover, the filtering of duplicate
    readings, estimation.
- **card-ledger-queue.**
  - **Mechanism:** duplicate messages are detected by a fingerprint of transaction fields that
    omits the network reference. Offline transactions (transit fares, tolls) have no
    authorization code and only a date, so distinct transactions on the same day share a
    fingerprint, and all but the first are discarded.
  - **Repair:** add the network reference to the fingerprint (one line).
  - **Plausible alternative causes:** out-of-order clearings parked and never posted, late
    presentments.
- **payroll-postmortem.**
  - **Mechanism:** a person's employment is taken to span from the start of their first contract
    row to the end of their last, so gaps between rows count as employed days. This affects
    salary, allowances and contribution ceilings.
  - **Repair:** bound employment by each row's end date, in the shared employment functions.
  - **Plausible alternative cause:** the divisor used to prorate salaries.
- **points-expiry.**
  - **Mechanism:** the job fixes its business date when it starts, but the expiry policy reads the
    current date again for each member. Members processed after midnight receive the next month's
    cutoffs.
  - **Repair:** pass the job's business date to the expiry policy (one line).
  - **Plausible alternative cause:** the arithmetic of the cutoff dates.
- **refund-postmortem.**
  - **Mechanism:** a new version of the provider's interface sends one event per status change of
    a refund (pending, then succeeded or failed), with the same refund identifier. The program
    books every event as a separate refund.
  - **Repair:** keep the last event of each refund, and count a refund only if its final status
    is "succeeded".
  - **Plausible alternative causes:** refunds of earlier months' charges, currency conversion,
    and excluding pending refunds, which repairs only part of the difference.
- **stock-allocation.**
  - **Mechanism:** the quantity available to marketplace lines is the stock left minus a safety
    stock, which is negative for locations below their safety stock. A test for a non-zero rather
    than a positive quantity lets negative picks through, creating phantom stock and
    over-shipping from the next warehouse.
  - **Repair:** take only positive quantities (one line).
  - **Plausible alternative cause:** the conversion of multipacks (the defect report's example is
    a 3-pack).

### Conditions

The four conditions differ only in one paragraph of the prompt, in whether a trace is supplied, and
in the software installed. The prompt is otherwise identical in all runs. It contains:
- the sentence "There may be a bug in the Python program in /work.";
- the paragraph describing the available tools;
- the instruction to find the bug and repair it with a minimal change;
- the instruction to end with a line naming the repaired file and function and stating the cause.

1. **Baseline (no trace).** The paragraph states that Python 3 and its debugger are installed. No
   trace is supplied.
2. **Query language.** The trace is supplied, and pmdb's command-line program is installed. The
   paragraph states this, instructs the agent to use pmdb and the trace, and contains a 347-word
   reference to the query language ([harness/query_reference.txt](../harness/query_reference.txt)).
3. **Python library.** The trace is supplied, and pmdb's Python library is installed and
   importable. The paragraph states this, instructs the agent to use the library and the trace,
   and contains a 339-word reference to the library
   ([harness/python_reference.txt](../harness/python_reference.txt)).
4. **Format specification.** The trace is supplied, and no software for reading it is installed.
   The paragraph instructs the agent to use the trace, writing its own reader if needed, and
   contains a 358-word specification of the trace's binary format
   ([harness/format_reference.txt](../harness/format_reference.txt)).

**Common to conditions 2–4:**
- **The trace is the same.** It is produced, for each run, by executing the program on the private
  input under pmdb's recorder. The recorder captures all calls automatically, without
  annotations in the code.
- **Agents are required to use the trace,** so whether they would choose to is not measured.
- **The reference text is always in the prompt.** No further documentation is provided in any
  condition.

**Software versions:**
- **recorder and Python library:** commit `659d619` (unchanged since `9003d9d`);
- **command-line program:** built from the sources at commit `ebc8a19`.

In the harness and the results, the conditions are labelled A (baseline), Q (query language), P
(Python library) and F (format specification).

### Environment

Each run executes in an isolated sandbox (bubblewrap) containing:
- the exercise in a writable directory;
- the trace, in conditions 2–4;
- Python 3 and standard command-line tools;
- the software of its condition, and nothing else of pmdb.

**Network.** The sandbox has no network access, except to the model provider's interface through
a relay.

**Isolation.**
- The private input and the oracle are never visible to the agent.
- Copies of this repository present elsewhere on the machine are hidden.
- The recorder is available only while the trace is being produced.

**Agent configuration.** The agent may use six tools (shell, read, edit, write, search by
content, search by name). It has no web access and no subagents. Each run is limited to 80 turns
and 24 minutes.

### Procedure

- **Sample:** 4 conditions × 6 exercises × 3 models × 1 repetition, giving 72 runs.
- **Order:** the order of runs is drawn at random with a fixed seed (14). It is then sorted so
  that runs with Haiku start first and runs with Opus last, as earlier measurements showed Opus's
  runs to be the shortest.
- **Concurrency:** up to 36 runs execute concurrently, which the machine's memory allows. The
  study is expected to complete in about 40 minutes.
- **Interruptions:** a run interrupted by a service error or a usage limit is repeated rather than
  counted.

### Measures

- **Success:** the oracle accepts the repaired program.
  - It executes the final source code on several hidden inputs, which include variants of the
    triggering condition, and on the original input.
  - It requires every reported figure to be correct.
  - Partial repairs are therefore failures, e.g. excluding pending refunds instead of keeping each
    refund's last event, or correcting the salary but not the allowances.
- **Localization:** whether the file and function named in the agent's final line are those of the
  reference repair. This is checked by hand where the agent repaired a different place than the
  reference repair, as some correct repairs are possible elsewhere.
- **Cost:**
  - **Tokens:** the total processed by the model (uncached input, cache writes, cache reads and
    output), summed over the whole session. For a run that reached the time limit, it is summed
    over the model's responses.
  - **Tool calls and turns.**
  - **Elapsed time.**
- **Use of the trace:** from each run's transcript:
  - the number of queries and failed queries (condition 2);
  - the number of scripts using the library (condition 3);
  - the reader written and the corrections it needed (condition 4);
  - exports from the query language to other tools (condition 2).

### Analysis

- **Per run:** success, tokens and tool calls.
- **Per model and condition** (models are not pooled):
  - successes, out of 6;
  - localizations, out of 6;
  - median tokens;
  - tokens relative to the baseline run of the same exercise and model, as a geometric mean over
    exercises, over all runs and over the exercises that both runs repaired;
  - tokens per success.

With one run per combination, a difference of one or two successes is within chance.

### Threats to validity

- **Construction of the exercises.**
  - The exercises were written by Claude Opus 5.5, one of the models under evaluation, and
    designed so that the decisive evidence is present only at run time. They establish where a
    trace can help, not how often real defects have this form.
  - Their naming, structure and decoys may favour these models.
  - One exercise (billing-postmortem) was converted from an exercise in which the input was
    available, so its program and defect were not designed for the absence of the input.
  - Two exercises (billing-postmortem, refund-postmortem) have no incorrect repairs for the
    validation to reject. Their oracles still reject partial repairs through hidden inputs with
    variants of the triggering condition.
- **Sample size.** Six exercises with one defect each and one run per combination are few.
  The particularities of individual exercises, and the run-to-run variance (which is large for
  Haiku), weigh heavily.
- **Mandatory use of the trace.** Agents in conditions 2–4 must use the trace, and so incur its
  cost even when reading the code would suffice. Agents in condition 1 never see the decisive
  data, and can succeed only by reasoning from the code, logs and reports.
- **Residual hints.** The logs and reports in the workspace are those of the failing execution.
  They contain the incorrect figures, but not the expected ones.
- **Other defects.** The programs may contain other imperfections that an agent can reasonably
  call a bug. Repairing one of them instead of the planted defect counts as a failure.
- **Unequal references.** The references to the query language and the library summarize larger
  interfaces, whereas the format specification is complete. In conditions 2 and 3, agents may
  also export data and analyse it in Python.
- **Time limit and concurrency.**
  - The 24-minute limit may cut short a few runs that would have succeeded with more time.
  - Running 36 sessions concurrently may slow the runs or trigger rate limits.
- **No self-report.** No questionnaire is administered after the runs, so agents' own accounts of
  their difficulties are not collected.

## Results

Each cell: success (✓ or ✗), tokens / tool calls.

| exercise | model | 1. baseline | 2. query language | 3. Python library | 4. format specification |
|---|---|---|---|---|---|
| billing-postmortem | Haiku | ✗ 2,088k / 48 | ✗ 1,830k / 48 | ✗ 2,176k / 53 | ✗ 1,158k / 29 |
| billing-postmortem | Sonnet | ✓ 1,590k / 41 | ✓ 934k / 31 | ✓ 487k / 19 | ✓ 953k / 27 |
| billing-postmortem | Opus | ✓ 71k / 6 | ✓ 123k / 8 | ✓ 126k / 8 | ✓ 138k / 8 |
| card-ledger-queue | Haiku | ✗ 784k / 28 | ✗ 843k / 26 | ✗ 386k / 18 | ✗ 554k / 20 |
| card-ledger-queue | Sonnet | ✗ 726k / 31 | ✓ 2,163k / 52 | ✓ 1,312k / 41 | ✓ 3,327k / 63 |
| card-ledger-queue | Opus | ✓ 101k / 7 | ✓ 214k / 12 | ✓ 128k / 9 | ✓ 108k / 7 |
| payroll-postmortem | Haiku | ✗ 1,941k / 46 | ✗ 4,801k / 77 | ✗ 4,265k / 75 | ✗ 2,567k / 54 |
| payroll-postmortem | Sonnet | ✗ 3,762k / 65 | ✓ 3,598k / 63 | ✓ 1,745k / 45 | ✗ 3,344k / 60 |
| payroll-postmortem | Opus | ✓ 142k / 9 | ✓ 201k / 11 | ✓ 176k / 10 | ✓ 233k / 9 |
| points-expiry | Haiku | ✗ 1,966k / 41 | ✗ 2,005k / 55 | ✗ 2,966k / 64 | ✗ 1,727k / 37 |
| points-expiry | Sonnet | ✓ 742k / 28 | ✓ 1,184k / 34 | ✓ 2,648k / 54 | ✓ 1,576k / 42 |
| points-expiry | Opus | ✓ 93k / 6 | ✓ 110k / 7 | ✓ 74k / 5 | ✓ 108k / 7 |
| refund-postmortem | Haiku | ✗ 624k / 25 | ✗ 471k / 21 | ✗ 1,217k / 29 | ✗ 2,294k / 51 |
| refund-postmortem | Sonnet | ✗ 1,694k / 43 | ✗ 2,094k / 50 | ✗ 1,483k / 46 | ✗ 2,027k / 36 |
| refund-postmortem | Opus | ✗ 364k / 11 | ✗ 540k / 16 | ✗ 512k / 21 | ✗ 395k / 14 |
| stock-allocation | Haiku | ✓ 486k / 28 | ✓ 476k / 19 | ✓ 1,052k / 31 | ✓ 595k / 28 |
| stock-allocation | Sonnet | ✓ 471k / 26 | ✓ 1,241k / 35 | ✓ 655k / 26 | ✓ 1,935k / 52 |
| stock-allocation | Opus | ✓ 146k / 9 | ✓ 102k / 6 | ✓ 91k / 6 | ✓ 114k / 7 |

**Per model and condition.** Successes and localizations are out of 6 runs (6 exercises × 1
run).
- **Localized:** the run named or edited the function of the planted defect, whether or not its
  repair passed the oracle.
- **Round 13:** the successes of round 13, which ran the same exercises and conditions with the
  defect reports.
- **Costs:** ratios to the baseline run of the same exercise and model (geometric mean). "Pairs"
  counts only the exercises both runs repaired, with their number in parentheses.

| condition | successes | localized | round 13 successes | median tokens | tokens relative to the baseline, all runs | the same, pairs | tokens per success |
|---|---|---|---|---|---|---|---|
| **Haiku** | | | | | | | |
| 1. baseline | 1/6 | 1/6 | 4/6 | 1,362k | 1 | 1 | 7,889k |
| 2. query language | 1/6 | 1/6 | 3/6 | 1,337k | 1.10× | 0.98× (1) | 10,427k |
| 3. Python library | 1/6 | 2/6 | 3/6 | 1,696k | 1.39× | 2.17× (1) | 12,062k |
| 4. format specification | 1/6 | 1/6 | 2/6 | 1,442k | 1.13× | 1.23× (1) | 8,895k |
| **Sonnet** | | | | | | | |
| 1. baseline | 3/6 | 3/6 | 5/6 | 1,166k | 1 | 1 | 2,995k |
| 2. query language | 5/6 | 6/6 | 6/6 | 1,668k | 1.43× | 1.35× (3) | 2,243k |
| 3. Python library | 5/6 | 6/6 | 6/6 | 1,398k | 1.02× | 1.15× (3) | 1,666k |
| 4. format specification | 4/6 | 5/6 | 6/6 | 1,981k | 1.72× | 1.74× (3) | 3,290k |
| **Opus** | | | | | | | |
| 1. baseline | 5/6 | 5/6 | 5/6 | 122k | 1 | 1 | 184k |
| 2. query language | 5/6 | 6/6 | 6/6 | 162k | 1.36× | 1.34× (5) | 258k |
| 3. Python library | 5/6 | 6/6 | 6/6 | 127k | 1.11× | 1.06× (5) | 221k |
| 4. format specification | 5/6 | 6/6 | 6/6 | 126k | 1.22× | 1.25× (5) | 219k |

## Findings

- **Opus found the planted defect without being told the symptom.** It repaired 5 of 6 exercises
  in every condition, as many as in round 13 with the defect reports, and at about the same cost
  (median 122–162k tokens). Even without the trace, reading the code and the production reports
  was enough for every exercise except refund-postmortem.
- **The trace helped Sonnet localize the defect.**
  - **Without the trace,** Sonnet repaired 3 of 6. On card-ledger-queue, payroll-postmortem and
    refund-postmortem it repaired something else instead: a cash-transaction rule, a payslip
    check, and the currency of fees.
  - **With the trace,** it localized the planted defect in 5 or 6 of 6 exercises, and repaired 4
    or 5.
- **Refund-postmortem was repaired by no run.**
  - **With the trace,** Sonnet and Opus localized the defect in every condition (one event per
    status change, all booked), but their repairs disagreed with the expected figures:
    - Opus kept each refund's last event, but still counted the refunds pending at month end
      (€782.29 too high);
    - Sonnet excluded pending events, but still counted refunds re-sent after succeeding (7
      updates and 3 reversals), €368.71 too high.
  - **Without the trace,** both repaired unrelated code: an exchange-rate counter (Opus) and the
    currency of fees (Sonnet).
  - **What was missing.** With the defect report, the trace runs of round 13 had a target figure
    (NovaPay's €11,938.78) against which to check their repair. Here they had none, so the
    question of which statuses count was left to guesswork.
- **Haiku repaired only stock-allocation,** in every condition. Elsewhere it repaired unrelated
  code (summaries, checks, fee computation), with or without the trace.
- **Costs per model:**
  - **Opus:** 1.06–1.34× the baseline's tokens on the exercises both runs repaired, the Python
    library being the cheapest again.
  - **Sonnet:** 1.15–1.74×. Its tokens per success were lower with the query language and the
    library than without the trace (2,243k and 1,666k against 2,995k), because it repaired more
    exercises.

## Consequences

- **Without a symptom, the trace is a way to find what is wrong,** not only to confirm a
  hypothesis. For Sonnet, it raised localizations from 3 to 5–6 of 6. For Opus, which localized
  almost everything by reading, it changed little.
- **A trace does not replace the expected result.** In refund-postmortem, all trace runs found the
  mechanism, but none chose the right counting rule without a figure to reconcile against. The
  defect report contributes information that the trace does not.
- **These exercises are readable.** Opus finds 5 of 6 planted defects from the code and the
  production outputs alone, so their defects are visible to a careful reader once the right
  files are read.
