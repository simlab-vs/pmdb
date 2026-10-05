# Round 11 (quick, exploratory): the trace with pmdb's query language, no skill: report

18 runs in arm D: three post-mortem scenarios × Haiku, Sonnet and Opus 5.5 × 2 repetitions, 8 at a
time.
- **What arm D got:** the trace and the pmdb command-line tool, with a 344-word reference to its
  query language in the prompt ([../harness/reference.txt](../harness/reference.txt)).
- **What it didn't get:** a skill, the Python library, or the trace format.
- **Comparisons:** round 10's arm C (the trace and its format only), round 9's arms A (no trace)
  and B (the Python library, required), and round 7's arm B (the command-line tool with a skill).
- **One run's usage is corrected,** as described in the protocol.

## Results

Each run: ✓ or ✗, tokens / tool calls.

| scenario | model | D r11 (query language) | C r10 (format only) | A r9 (no trace) | B r9 (Python library) | B r7 (CLI + skill) |
|---|---|---|---|---|---|---|
| card-ledger-queue | haiku | ✗ 4,265k/67, ✗ 4,042k/79 | ✓ 2,727k/49, ✓ 1,208k/27 | ✓ 900k/22, ✗ 575k/18 | ✗ 4,440k/80, ✗ 5,184k/80 | ✗ 4,771k/80, ✗ 3,564k/64 |
| card-ledger-queue | sonnet | ✓ 1,227k/33, ✓ 693k/24 | ✓ 1,589k/40, ✓ 1,114k/35 | ✓ 558k/23, ✓ 937k/30 | ✗ 2,534k/48, ✓ 1,468k/37 | ✓ 1,338k/34, ✓ 713k/23 |
| card-ledger-queue | opus | ✓ 180k/8, ✓ 148k/10 | ✓ 227k/10, ✓ 156k/9 | ✓ 137k/9, ✓ 101k/7 | ✓ 204k/11, ✓ 177k/10 | ✓ 228k/12, ✓ 190k/9 |
| payroll-postmortem | haiku | ✓ 1,862k/50, ✗ 4,238k/80 | ✗ 3,577k/60, ✗ 4,280k/71 | ✗ 5,237k/80, ✗ 2,279k/51 | ✗ 1,681k/41, ✗ 5,010k/65 | ✓ 1,584k/36, ✓ 3,436k/63 |
| payroll-postmortem | sonnet | ✓ 4,266k/66, ✓ 1,282k/34 | ✓ 1,509k/37, ✓ 1,109k/33 | ✓ 993k/32, ✓ 883k/32 | ✓ 1,794k/40, ✓ 1,055k/29 | ✓ 1,302k/36, ✓ 1,922k/46 |
| payroll-postmortem | opus | ✓ 168k/9, ✓ 223k/11 | ✓ 166k/8, ✓ 183k/9 | ✓ 132k/7, ✓ 155k/10 | ✓ 238k/10, ✓ 120k/7 | ✓ 203k/10, ✓ 390k/13 |
| refund-postmortem | haiku | ✗ 3,144k/69, ✗ 2,828k/58 | ✗ 2,831k/51, ✗ 2,476k/47 | ✗ 457k/19, ✗ 440k/23 | ✗ 2,219k/53, ✗ 2,422k/58 | ✗ 3,349k/63, ✓ 2,436k/52 |
| refund-postmortem | sonnet | ✓ 2,676k/55, ✓ 3,747k/68 | ✓ 2,733k/48, ✓ 2,745k/55 | ✗ 1,217k/33, ✗ 1,242k/30 | ✓ 2,114k/47, ✗ 4,339k/70 | ✓ 2,913k/52, ✓ 2,124k/48 |
| refund-postmortem | opus | ✓ 234k/14, ✓ 239k/13 | ✓ 277k/13, ✓ 234k/12 | ✗ 166k/8, ✗ 221k/11 | ✓ 399k/21, ✓ 199k/9 | ✓ 370k/14, ✓ 386k/16 |

| arm | successes (Haiku / Sonnet / Opus) | median tokens / tool calls |
|---|---|---|
| D, round 11: query language in the prompt | 13/18 (1 / 6 / 6) | 1,572k / 42 |
| C, round 10: format only | 14/18 (2 / 6 / 6) | 1,359k / 36 |
| B, round 7: command line + skill | 15/18 (3 / 6 / 6) | 1,461k / 36 |
| B, round 9: Python library | 10/18 (0 / 4 / 6) | 1,738k / 40 |
| A, round 9: no trace | 9/18 (1 / 4 / 4) | 566k / 22 |

## Findings

- **Sonnet and Opus: as with every other trace arm.** They fixed all 12 runs, including refund,
  which they failed in all 12 runs without the trace in rounds 7–9.
  - **Opus** was the cheapest trace arm on card-ledger (148–180k tokens, 8–10 calls) and refund
    (234–239k, 13–14 calls).
  - **Sonnet's** cost varied most. One payroll run took 4.3M tokens and 66 calls.
- **Haiku: 1 of 6.** It succeeded once on payroll, but failed both card-ledger runs, which
  round 10's Haiku had solved with its own reader.
  - Its card-ledger failures ended on wrong causes: hold states, and FX amounts in the
    fingerprint.
  - Its refund failures are the familiar ones: excluding pending refunds, or a partial
    deduplication.
  - It used 9–32 pmdb commands per run. Most failed commands were a shell pipe inside the heredoc
    (`| head`, `| wc -l`), an undefined `$0` across invocations, or a string used as a condition.
- **Every run exported and analysed in Python.** All 18 used `export` (1–7 times) and then ran
  Python on the JSON Lines (1–32 scripts). The query language served as a selection and export
  front end, as in round 7.
  - **Opus** ran 3–5 pmdb commands per run, and **Sonnet** 4–7.
  - There were 20 failed pmdb commands in all, 17 of them in Haiku runs.
- **Against writing one's own reader (round 10):** about the same.
  - **Successes:** 13 against 14, with Sonnet and Opus identical.
  - **Cost:** slightly higher, 1,572k against 1,359k median tokens and 42 against 36 calls.
  - **Haiku** was the difference: 1/6 here, against 2/6 with the format.

## Consequences

- **The query language added no benefit over a documented format** on these tasks. Agents used
  it to select and export, then analysed in Python, which they could do equally well with their
  own reader.
- **A terse reference in the prompt is enough for strong models.** It has no skill, and Opus and
  Sonnet used pmdb correctly within a few commands. Weaker models still trip on the command-line
  conventions: pipes inside the heredoc, variables lasting one invocation.
- **Across rounds 7–11, the trace is what matters,** however it is accessed. Sonnet and Opus fix
  the refund post-mortem with any form of access to the trace, and never without it. The form of
  access mostly changes the cost, and Haiku's chances, which vary a lot from run to run.
- **These are 2 runs per cell on different days.** A powered comparison of C against D (and B)
  would be needed to separate them.
