# Usability study of pmdb, round 3 (protocol)

Written before any agent run. Changes after the first non-pilot run are listed at the end with
their reason.

## Questions

In rounds 1 and 2, agents in both arms usually found the bug by reading the code: the programs
were small, and round 1's mutation operators leave a visible oddity at the mutated site (a
flipped operator or a constant off by one). This round asks the questions of round 2 on
exercises built to resist reading:

1. **Usability (primary, qualitative):** how do agents use pmdb and the skill when reading the code
   isn't enough, and where do they struggle?
2. **Efficiency (secondary, quantitative):** on these exercises, does access to pmdb change how
   much effort an agent needs to fix a bug, compared with the same agent without it?

## Tool version

pmdb, the Python recorder and the skill `skills/pmdb` as used in round 2, at the `ci` commit
that adds this protocol (release build), frozen for the whole round.

## Exercises

The method differs from rounds 1 and 2 in four ways.

- **Programs.** Three new programs, larger than round 1's (`programs/`): a warehouse inventory
  with FIFO costing, a spreadsheet engine, and a sports league season. Each has 3-5 modules and a
  hidden random input generator. They print compact summaries aggregated from many intermediate
  values, so a wrong value deep inside shows up far from its cause. They were written by Claude
  (as before, a known limitation) under the instruction not to place any bug.
- **Mutation operators.** Round 1's operators, plus operators modelling bugs that read naturally
  (`harness/realistic.py`):
  - a variable read replaced by another local variable of the same function;
  - a copy (`list(x)`, `dict(x)`, `x.copy()`, …) replaced by the original;
  - the integer default of `d.get(k, n)` increased by one;
  - an augmented assignment removed;
  - `break` and `continue` exchanged;
  - the end of a non-constant `range` decreased by one.

  Up to 8 sites are sampled per operator and program with a fixed seed (`harness/mutate.py`),
  because `wrong-var` alone has far more sites than all other operators together. Each mutant runs
  on 300 generated inputs against the unmodified program.
- **Candidates** (`harness/select_exercises.py candidates`, fixed rule). A candidate must:
  - fail silently on the first failing generated input, which is the reported input;
  - fail on at most 25% of the inputs;
  - change at most a third of the output lines of the reported input;
  - be in a function called at a depth of at least 3 in the reported run, with `main` at 1.

  Candidates are ordered per program with a fixed seed.
- **Read-only screen** (`harness/screen.py`). In that order, each candidate is given to Sonnet in
  the study's sandbox, with only the tools Read, Grep and Glob, and with the actual and expected
  outputs. It must name the faulty function without running anything. Screening a program stops
  after 4 candidates that it does not localize ("hard") or after 8 screened candidates.
- **Selection** (`harness/select_exercises.py final`). Exercises are taken from the programs in
  turn until there are 10, from each program's hard candidates first, then from its localized
  ones ("easy"). There are no crash controls.

Selecting against a reading agent is deliberate: it operationalizes "can't easily be fixed by
reading the code". It favours exercises where running the program helps, which both arms can do
(arm A with prints and pdb). The screen uses one attempt per candidate, so "hard" is noisy.

## Arms, models, budget, sandbox

As in round 2 (`../round-2/PROTOCOL.md`): arm A gets Python 3 and pdb; arm B also gets pmdb in
`/opt/pmdb`, the skill as a user skill, a pre-recorded trace `/work/report.pmdb`, and one
sentence in the prompt. Claude Code 2.1.283, models `sonnet` and `haiku`, one run per exercise ×
arm × model (40 runs) plus 2 pilot runs on an extra candidate, excluded from the analysis.
Each run is capped at 60 turns and 20 minutes, two runs execute at a time, and a run interrupted
by a usage limit or an infrastructure error is run again.

## Measurements and analysis

As in round 2, with these categories: "hard" and "easy" by the screen's outcome instead of
round 1's rare, subtle and crash. In addition, it reports per exercise the screen's outcome next to
the success of each arm.

## Changes after the start

None: the round was abandoned before any run of the study (below).

## Outcome: abandoned after the screen

The screen localized every candidate (`data/screen.jsonl`): all 18 candidates (7 warehouse,
5 sheet, 6 league), in 7 to 11 turns and 64k to 235k tokens each, without running anything.
Candidates that the screen solved can't make "exercises that can't easily be fixed by reading
the code", so the user decided to source real bugs from real projects instead
(`../round-4/`). The selection rule's fallback (10 localized candidates) was not applied, and no
run of the study was made with these exercises.
