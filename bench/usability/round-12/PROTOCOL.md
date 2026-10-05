# Round 12: four forms of access to an execution trace (protocol)

This protocol was written before any run of the study.

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
- **Rounds 7–11 studied that setting** with five exercises of this kind. Agents without a trace
  failed every run of one exercise (refund-postmortem), while agents with a trace usually
  succeeded.
- **The form of access changed from round to round:**
  - pmdb's query language with an instructional document (round 7);
  - a Python library (rounds 8–9);
  - only a specification of the trace's file format, with agents writing their own readers
    (round 10);
  - the query language with a short reference (round 11).

  Success rates were similar, and costs differed modestly.
- **Those comparisons were confounded.** The rounds ran on different days, with different prompts
  and instructional material, and with two runs per combination of exercise and model.

This round compares the four conditions on the same day, with prompts that differ in a single
paragraph and without instructional material beyond that paragraph. It uses the three exercises on
which agents with pmdb performed worst in rounds 7–9.

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

**Design.** Each exercise describes a batch job that ran in production and produced incorrect
figures. The execution cannot be reproduced, because the data it processed is no longer available:
it was private and deleted after use, it was held only by an external system, or it was consumed
from a message queue. The agent receives:
- the program's source code;
- the job's log and the report it produced;
- a defect report written as a user would write it, giving the incorrect figures, the expected
  figures, and the reason the input cannot be provided.

**Origin.** The exercises were designed and written for this
study by Claude Opus 5.5. Each consists of:
- a program of 1,000–1,100 lines of Python in 13 to 18 modules, in a realistic business domain;
- a seeded generator of the private input, and a ground truth;
- the production log and report, produced by running the program on the private input;
- the defect report;
- a reference repair;
- one or more plausible but incorrect repairs;
- an oracle.

A validation script verifies, for each exercise, that:
- the reported symptom is reproduced by the original program;
- the oracle rejects the original program, accepts the reference repair, and rejects each
  incorrect repair;
- recording a trace leaves the exercise's files unchanged.

**Selection.** The study uses three exercises from a set of five constructed in this way. They
were chosen as the three with the lowest success rates among trace-equipped agents in a
preliminary study:

| exercise | why the execution cannot be reproduced | reported symptom |
|---|---|---|
| card-ledger-queue | the card processor's queue messages were consumed | debits €808.30 short of the bank's figures, on 202 cards |
| payroll-postmortem | the private HR export was deleted after payment | salaries €16,904.43 above HR's preview |
| refund-postmortem | the payment provider's export does not leave the production system | NovaPay refunds €5,027.67 (42%) too high |

### Defects

Each exercise contains exactly one defect, with these properties:
- the code is correct for the common case;
- a condition present in a minority of the input records makes the program produce incorrect
  totals;
- the program terminates normally, and its internal consistency checks pass;
- the condition is visible only in the input, which the trace records and the agent otherwise
  lacks.

| exercise | class of defect | mechanism | affected records |
|---|---|---|---|
| card-ledger-queue | incomplete identity key | Duplicate messages are detected by a fingerprint of transaction fields that omits the network reference. Offline card transactions (transit fares, tolls) carry no authorization code and only a date, so distinct transactions on the same day share a fingerprint, and all but the first are discarded as duplicates. | 280 transactions on 202 cards |
| payroll-postmortem | unchecked invariant on intervals | A person's employment is taken to span from the start of their first contract row to the end of their last. Gaps between rows therefore count as employed days, affecting salary, allowances and contribution ceilings. | 9 of about 650 persons |
| refund-postmortem | change in an external data model | A new version of the provider's interface sends one event per status change of a refund (pending, then succeeded or failed), with the same refund identifier. The program books every event as a separate refund. | 103 of 354 refunds |

**Reference repairs:**
- **card-ledger-queue:** add the network reference to the fingerprint (one line).
- **payroll-postmortem:** bound employment by each row's end date, in the shared employment
  functions.
- **refund-postmortem:** keep the last event of each refund, and count a refund only if its final
  status is "succeeded".

**What makes the defects hard to find by reading.** Several features of each exercise make
localization by reading costly without making it impossible:
- the defective code is documented and appears deliberate;
- the triggering condition is not apparent from the code;
- each exercise contains plausible alternative causes, e.g. the handling of out-of-order messages,
  the proration of salaries, and refunds still pending at month end;
- the log reports only aggregates.

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

- **Sample:** 4 conditions × 3 exercises × 3 models × 1 repetition, giving 36 runs.
- **Order:** the order of runs is drawn at random with a fixed seed (12). It is then sorted so
  that runs with Haiku start first and runs with Opus last, as earlier measurements showed Opus's
  runs to be the shortest.
- **Concurrency:** up to 24 runs execute concurrently, so that the study completes in about 30
  minutes.
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

The analysis is descriptive.
- **Per run:** success, tokens and tool calls, for each exercise, model and condition.
- **Per condition and model:** successes and median cost.
- **Comparison:** the same measures from earlier runs of these exercises, as an indication of
  run-to-run variance.

With a single run per combination of exercise, model and condition, a difference of one or two
successes between conditions is within the variation expected by chance. The study is designed to
compare the conditions under identical circumstances, not to estimate effect sizes precisely.

### Threats to validity

- **Construction of the exercises.**
  - The exercises were written by the family of models under evaluation, and designed so that the
    decisive evidence is present only at run time. They establish where a trace can help, not how
    often real defects have this form.
  - Their naming, structure and decoys may favour these models.
- **Sample size.** Three exercises with one defect each and one run per combination are few. The
  particularities of individual exercises, and the run-to-run variance (which is large for
  Haiku), weigh heavily.
- **Mandatory use of the trace.** Agents in conditions 2–4 must use the trace, and so incur its
  cost even when reading the code would suffice. Agents in condition 1 never see the decisive
  data, and can succeed only by reasoning from the code, log and report.
- **Unequal references.** The references to the query language and the library summarize larger
  interfaces, whereas the format specification is complete. In conditions 2 and 3, agents may
  also export data and analyse it in Python.
- **Time limit and concurrency.**
  - The 24-minute limit may cut short a few runs that would have succeeded with more time.
  - Running 24 sessions concurrently may slow the runs or trigger rate limits.
- **No self-report.** No questionnaire is administered after the runs, so agents' own accounts of
  their difficulties are not collected.
