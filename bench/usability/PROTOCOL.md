# Exploratory usability study of pmdb (protocol)

Written before any agent run. Changes after the first non-pilot run are listed at the end with
their reason.

## Questions

1. **Usability (primary, qualitative):** how do coding agents use pmdb and the Python recorder,
   where do they struggle, and what do they ask for?
2. **Efficiency (secondary, quantitative):** on generated debugging exercises, does access to pmdb
   change how much effort an agent needs to fix a bug, compared with the same agent without it?

## Tool version

pmdb and the recorder at `ci` commit `a9cb57d` (release build), frozen for the whole study.
Usability problems found during the study are reported, not fixed.

## Exercises

- Four programs written for this study (`programs/`): invoicing, a calculator language, a room
  scheduler and a route planner, each with a hidden random input generator. The unmodified
  program is the oracle. They were written by Claude (the model that designed the study), which
  is a known limitation; no bug was placed by hand.
- `harness/mutate.py` enumerates mutation sites inside function bodies (comparison, arithmetic
  and boolean operator flips, integer constants ±1, dropped `not`, `min`/`max` swaps and swapped
  call arguments). It samples 60 sites per program with a fixed seed and runs each mutant on 300
  generated inputs against the oracle.
- `harness/select_exercises.py` picks the exercises with a fixed rule and seed. For each program
  it picks one *rare* silent mutant (wrong output, no exception, failing on at most 10% of inputs)
  and one *subtle* silent mutant (failing on 10–90%). It adds two *crash* controls from two random
  programs. That gives 10 exercises. The reported input is the first failing generated input.
- Known quirks of the drawn set, kept because the rule produced them: two calc exercises mutate
  the same line; ex08 changes a constant (a left-turn penalty); ex07 changes tie-breaking among
  routes of equal cost.

## Arms

- **A (baseline):** the sandbox contains the program, the failing input and the expected output.
  The prompt says Python 3 (including pdb) is available.
- **B (pmdb):** the same, plus `/opt/pmdb` (pmdb, the recorder, `pmdb-record`, and a README whose
  query-language section is the repository README verbatim). It also gets a trace of the failing
  run recorded in advance at `/work/report.pmdb`, and one sentence in the prompt pointing to both.

The prompts are otherwise identical (`harness/prompts.py`).

## Models and budget

Claude Code 2.1.283 in headless mode, using the user's Claude subscription. The models are the
`sonnet` and `haiku` aliases, with the resolved model IDs recorded from each run. One run per
exercise × arm × model gives **40 runs**, plus 2 pilot runs on an extra exercise that are
excluded from the analysis. Runs are executed in a random order (fixed seed), two at a time.
Each run is capped at 60 turns and 20 minutes.

A run interrupted by a subscription usage limit or an infrastructure error is discarded and run
again from scratch later. It is never counted as a failure, because the pmdb arm makes more tool
calls and would be cut off more often.

## Sandbox and the agent's knowledge

Each run happens in a bubblewrap sandbox:
- **Filesystem:** a read-only `/nix` store, a minimal `/etc` (DNS, hosts, CA certificates, a
  `passwd` entry for user `agent`), a fresh `$HOME`, the writable `/work` and, in arm B only, a
  read-only `/opt/pmdb`. Nothing from the host home directory, the repository, the study files,
  the oracle or the generators is visible.
- **Namespaces:** all are unshared except the network, which Claude Code needs to reach the API.
- **Claude Code:** user/project settings, CLAUDE.md files and MCP servers are disabled. The only
  tools are Bash, Read, Edit, Write, Grep and Glob (no web access, no subagents), and they are
  pre-approved in `dontAsk` mode.
- **Prompt:** the prompt does not mention the study; the feedback questions are asked only after
  the task has ended.

## Measurements

For each run:
- success: the final program matches the oracle on the reported input and on all 300 generated
  inputs;
- localization: the function named in the final `RESULT:` line is the mutated function;
- number of turns, wall time, input/output/cache tokens and number of tool calls;
- number of pmdb and `pmdb-record` invocations and how many failed;
- the diff of the fix.

After the task, the same session answers a fixed feedback questionnaire (`harness/prompts.py`),
returned as JSON.

## Analysis (fixed in advance)

- **Primary quantitative comparison:** the paired difference B − A in total tokens processed
  (input + cache read + cache creation + output) and in turns, over the 20 exercise × model
  pairs, using a two-sided Wilcoxon signed-rank test at α = 0.05. Success is compared with an
  exact McNemar test on the same pairs. With 20 pairs only large effects can reach significance;
  results are reported with effect sizes (median paired difference, with a bootstrap 95% CI)
  whether significant or not.
- **Descriptive only:** breakdowns by category (rare / subtle / crash) and by model.
- **Usability:** a thematic summary of the questionnaires and of the transcripts:
  - every pmdb error message an agent hit;
  - queries that returned nothing and were reworded;
  - documentation the agents misread;
  - features they asked for.

## Changes after the start

(none yet)
