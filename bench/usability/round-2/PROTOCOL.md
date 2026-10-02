# Usability study of pmdb, round 2 (protocol)

Written before any agent run. Changes after the first non-pilot run are listed at the end with
their reason.

## Questions

Round 1 (`../round-1/`) found that agents in the pmdb arm lost time to pmdb's command line, to
gaps in its documentation and to missing features. pmdb was changed in response (see
`bench/RESEARCH_LOG.md`), and agents now get an agent skill instead of a README. This round
re-runs round 1's exercises to ask:

1. **Usability (primary, qualitative):** do agents still hit the problems of round 1, and which
   new problems appear with the current pmdb and the skill?
2. **Efficiency (secondary, quantitative):** with the same exercises, does access to pmdb change
   how much effort an agent needs to fix a bug, compared with the same agent without it?

## Tool version

pmdb, the Python recorder and the skill `skills/pmdb` at the `ci` commit that adds this protocol
(release build), frozen for the whole round. The commit is recorded in the results. Usability
problems found during the round are reported, not fixed.

## Exercises

Round 1's exercises, unchanged: `data/` holds copies of round 1's `mutants.json`,
`exercises.json` and `plan.json`. The plan fixes the 10 exercises, the pilot exercise, and the
order of the runs, which are the same as in round 1.

## Arms

- **A (baseline):** as in round 1. The sandbox contains the program, the failing input and the
  expected output. The prompt says Python 3 (including pdb) is available.
- **B (pmdb):** the same, plus:
  - `/opt/pmdb`, holding pmdb (on `PATH`) and the Python recorder (on `PYTHONPATH`);
  - the skill, installed as a Claude Code user skill in `~/.claude/skills/pmdb`, with its scripts
    `pmdb-record` and `clip`;
  - the `Skill` tool, for the pmdb skill only. Claude Code also lists its bundled skills, which
    can't be hidden, so permission rules deny each of them (`harness/skill_check.py` checks that
    `pmdb` can be invoked and a bundled skill can't);
  - a trace of the failing run, recorded in advance at `/work/report.pmdb` with the skill's
    `pmdb-record`;
  - one sentence in the prompt saying that pmdb and a skill describing it are installed and that
    the trace exists. The prompt doesn't name the skill's location or tell the agent to use it.

The prompts are otherwise identical (`harness/prompts.py`). Both arms now read user settings
(`--setting-sources user`) so that Claude Code finds the skill. The home directory is created
empty for each run, so arm A has no user settings.

## Models and budget

As in round 1: Claude Code 2.1.283 in headless mode, using the user's Claude subscription, and the
models are the `sonnet` and `haiku` aliases, with the resolved model IDs recorded from each run.
One run per exercise × arm × model gives **40 runs**, plus the 2 pilot runs, which are excluded
from the analysis. Runs are executed in the plan's order, two at a time, and each is capped at 60
turns and 20 minutes. A run interrupted by a usage limit or an infrastructure error is discarded
and run again from scratch later.

## Sandbox and the agent's knowledge

As in round 1 (bubblewrap; read-only `/nix`, minimal `/etc`, fresh `$HOME`, writable `/work`,
read-only `/opt/pmdb` in arm B; no MCP servers, no project settings or CLAUDE.md files; tools
Bash, Read, Edit, Write, Grep and Glob, plus Skill in arm B, pre-approved in `dontAsk` mode). The
prompt doesn't mention the study, and the feedback questionnaire is asked after the task.
`harness/probe_sandbox.py` and `harness/skill_check.py` check the sandbox and the skills before the
runs.

## Measurements

Those of round 1 (success on the reported input and on 300 generated inputs, localization,
turns, wall time, tokens, tool calls, pmdb and `pmdb-record` invocations and failures, the fix's
diff, and the feedback questionnaire), plus, in arm B, whether and when the agent invoked the
skill and how often it used `clip`.

## Analysis (fixed in advance)

- **Within this round:** the analysis of round 1: the paired differences B − A in total tokens
  and in turns over the 20 exercise × model pairs (two-sided Wilcoxon signed-rank test,
  α = 0.05, median paired difference with a bootstrap 95% CI), and success compared with an exact
  McNemar test; breakdowns by category and model, descriptive only.
- **Against round 1 (descriptive only):** for each arm, the same metrics next to round 1's, and
  for arm B the number of failed pmdb invocations per run and the questionnaire's
  `pmdb_usefulness`. Round 1 and this round ran at different times, possibly with different
  models behind the aliases, so differences between rounds are not attributed to pmdb unless arm
  A stays stable.
- **Usability:** as in round 1, a thematic summary of the questionnaires and the transcripts:
  every pmdb error message, queries that returned nothing and were reworded, documentation the
  agents misread, and features they asked for, each compared with round 1's findings.

## Changes after the start

None.
