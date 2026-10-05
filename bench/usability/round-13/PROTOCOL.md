# Round 13: four forms of access to an execution trace, six exercises (protocol)

This protocol was written before the runs, except the analysis of refund-postmortem, which was
added after them.

The document has two parts:
- **Background** relates this round to the earlier rounds of the usability study and explains why
  it is designed as it is.
- **Methodology** describes the study itself, and is meant to be read on its own, without
  reference to earlier rounds.

## Background: earlier rounds

Earlier rounds of the study (see [../../RESEARCH_LOG.md](../../RESEARCH_LOG.md)) evaluated pmdb,
a debugger that answers queries over recorded execution traces, with coding agents.

- **Rounds 1–3 used mechanically generated defects** (mutants) in small and medium programs. A
  model that only reads the code localized them; a reading-only screen localized all 18
  candidates of round 3.
- **Rounds 4–5 used real defects sourced from GitHub.** They were localized from their failing
  tests (when provided), or were unsolvable from the issue text alone.
- **Round 6 built six exercises intended to require runtime evidence.** Only the one in which the
  failing execution could not be reproduced (a "post-mortem" exercise) distinguished agents that
  had a trace from agents that did not.
- **Rounds 7–11 studied that setting** with five exercises of this kind, in different forms of
  access to the trace: a query language, a Python library, and a format specification alone.
  These comparisons were confounded by differences in day, prompt and instructional material.
- **Round 12 compared the four forms of access** under identical conditions, on three of the five
  exercises with one run per combination.

Round 13 repeats round 12's design on twice as many exercises:
- all five post-mortem exercises of rounds 7–11;
- a sixth, `billing-postmortem`, converted from round 6's `billing-needle`.

The conversion withholds the input data from the agent and supplies the production run's
outputs instead:
- the data moved to `private/`;
- the agent gets the summary, the exceptions report and the log;
- the defect report explains why the data cannot be provided;
- the recording script and the validation were adapted.

The program, the defect, the hidden inputs and the oracle are unchanged.

## Methodology

### Research question

When an automated coding agent must diagnose and repair a defect from the record of a failed
execution that cannot be reproduced, how do its success rate and its cost depend on the form in
which that record is made available? We compare four conditions: no record; a query language over
the record; a Python library over the record; and a specification of the record's file format
alone.

### Terms

- **Agent:** an instance of Claude Code (an AI coding assistant) running non-interactively. It
  works with a fixed set of tools: running shell commands, and reading, searching and editing
  files.
- **Model:** the language model driving the agent: Claude Haiku 4.5, Claude Sonnet 5 or Claude
  Opus 5.5.
- **Exercise:** a program containing one defect, together with a report of the defect's effect on
  one production execution and the material available about that execution.
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

Each exercise describes a batch job that ran in production and produced incorrect figures, and
whose execution cannot be reproduced because the data it processed is no longer available. The
agent receives:
- the program's source code;
- the job's log and the reports it produced;
- a defect report written as a user would write it, giving the incorrect figures, the expected
  figures, and the reason the input cannot be provided.

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
- the defect report;
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
- the defect report;
- the paragraph describing the available tools;
- the instruction to identify the root cause and repair it with a minimal change;
- the instruction to end with a line naming the repaired file and function and stating the cause.

1. **Baseline (no trace).** The paragraph states that Python 3 and its debugger are installed. No
   trace is supplied.
2. **Query language.** The trace is supplied, and pmdb's command-line program is installed. The
   paragraph states this, instructs the agent to use pmdb and the trace, and contains a 347-word
   reference to the query language ([harness/query_reference.txt](harness/query_reference.txt)).
3. **Python library.** The trace is supplied, and pmdb's Python library is installed and
   importable. The paragraph states this, instructs the agent to use the library and the trace,
   and contains a 339-word reference to the library
   ([harness/python_reference.txt](harness/python_reference.txt)).
4. **Format specification.** The trace is supplied, and no software for reading it is installed.
   The paragraph instructs the agent to use the trace, writing its own reader if needed, and
   contains a 358-word specification of the trace's binary format
   ([harness/format_reference.txt](harness/format_reference.txt)).

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
- **Order:** the order of runs is drawn at random with a fixed seed (13). It is then sorted so
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
  - median tokens;
  - tokens relative to the baseline run of the same exercise and model, as a geometric mean over
    exercises, over all runs and over the exercises that both runs repaired;
  - tokens per success.

With one run per combination, a difference of one or two successes is within chance.

**The outlier: refund-postmortem.** In the other five exercises, the defect report and the log
(exact differences, which totals are unaffected, an example record, timestamps) admit only one
mechanism in the code, and the repair follows from the code alone. In refund-postmortem, the
mechanism can also be inferred: each status change of a refund arrives as a separate event. The
correct repair cannot, because it depends on facts about the input:
- which status sequences occur: refunds still pending at month end, refunds reversed after
  succeeding, intermediate statuses;
- how each of them must be counted.

Without the trace, agents repaired the mechanism but counted wrongly. With it, they read the
status sequences and reproduced the expected figure exactly.

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
- **Unequal references.** The references to the query language and the library summarize larger
  interfaces, whereas the format specification is complete. In conditions 2 and 3, agents may
  also export data and analyse it in Python.
- **Time limit and concurrency.**
  - The 24-minute limit may cut short a few runs that would have succeeded with more time.
  - Running 36 sessions concurrently may slow the runs or trigger rate limits.
- **No self-report.** No questionnaire is administered after the runs, so agents' own accounts of
  their difficulties are not collected.
