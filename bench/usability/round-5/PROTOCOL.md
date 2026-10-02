# Usability study of pmdb, round 5 (protocol)

Written before any agent run. Changes after the first non-pilot run are listed at the end with
their reason.

## Questions

Round 4 (`../round-4/`) gave agents real bugs with the failing tests named. The fixed tests stated
the cause, a read-only screen localized 20 of 22 bugs, and pmdb made no model more efficient. This
round keeps round 4's bugs, models and arms, but gives agents **the issue a user reported** instead
of the failing tests: the agent must reproduce the bug before it can diagnose it, and in the pmdb
arm it records its own reproduction.

1. **Efficiency and success (primary):** does access to pmdb change how much effort an agent needs
   to fix a reported issue, and how often it fixes it, compared with the same agent without it,
   for each of Haiku, Sonnet and Opus?
2. **Usability (qualitative):** how do agents reproduce, record and query on real projects, and
   where do they struggle?
3. **Models (qualitative):** how do the models differ in their methodology (how they reproduce
   and investigate), their mistakes, and the effort they waste, with and without pmdb?

## Changes from round 4, and why

- **Issues instead of failing tests.** In round 4 the fixed tests described the cause, often more
  precisely than a user would. The agent now gets the text of the GitHub issue(s) closed by the
  fix, and `/work` is the project at the parent commit with the fix's tests hidden. They still
  grade the fix. Agents may write tests; these don't count in grading. Only bugs whose fix's pull
  request closes an issue are used.
- **No network for agents.** In round 4 the sandbox kept the network for Claude Code, and agents
  and fixtures used it; pipx's tests needed it and were mis-graded offline. The sandbox now has no
  network at all; Claude Code reaches only the API, through a relay (below). Every check of
  `prepare.py` now runs offline in a fresh materialization, so a project whose tests need the
  network is excluded rather than passing on a cache downloaded by an earlier online run; pipx is
  excluded up front for that reason.
- **No pre-recorded trace.** Arm B no longer gets a trace of the failing tests (there are none to
  name). pmdb and the skill are available and the prompt says so; recording is the agent's job.
- **pmdb rebuilt** with the fixes made after round 4 (see the research log of 2026-10-02).
- **Limits:** 80 turns and 30 minutes per run (60 and 20 in round 4), since reproducing takes
  longer than running named tests; 8 runs at a time (round 4 ended with 16 on 14 cores).

## Tool version

pmdb, the Python recorder and the skill `skills/pmdb` at the `ci` commit `0c92b99` (the repository
HEAD when this round was set up), frozen for the whole round. Release build:
`swift build -c release --product pmdb --scratch-path bench/usability/round-5/_work/swift-build
-Xswiftc -file-prefix-map -Xswiftc "/home/ambrus/pytrace-recorder=/src"` from the repository
root, assembled with `harness/assemble.py` into `_work/opt-pmdb` (pmdb and the recorder) and
`_work/skill`. Usability problems found during the round are reported, not fixed.

## Exercises

### Bugs with issues (`harness/issues.py`; `data/issues.jsonl`, `data/bugs.jsonl`)

Round 4's 25 mined bugs (`../round-4/data/bugs.jsonl`; their mining is described in round 4's
protocol). The number of the fix's pull request is read from the commit message (`(#123)`), and
the issues it closes are its `closingIssuesReferences` in GitHub's GraphQL API. A bug is kept iff
it closes at least one issue: **18 of 25** (none of nltk, Gymnasium or needle; 2 of 4 pipx bugs).
Round 4's trees, environments and clones are reused read-only (environments are copied with
reflinks).

The **issue text** is the closing issues' titles and bodies, in issue-number order, separated by
`---`, with HTML comments (issue templates' instructions) removed. Comments on the issue and the
authors are not included. Nothing else is edited: an issue may suggest a cause or a fix, as
real reports do.

### The agent's view (`harness/bugs.py`)

- `/work`: the project at the **parent** commit, without `.git`, caches and build artifacts.
  Every file changed by the fix is at its parent version: source files, documentation and
  changelogs, and the fix's tests (hidden).
- `/opt/env` (read-only, first on `PATH`): a copy of the bug's environment, in which the editable
  install points at `/work`.
- No network (see Sandbox).

### Exclusion rules (`harness/prepare.py`, pre-registered; `data/prepared.jsonl`)

**pipx is excluded up front** (reason "excluded repository"), by the user's decision: its test
session downloads a package cache, so its tests need the network and time out offline (the first
preparation found its first bug not reproducible offline, slow and not recordable, each run taking
the 600 s timeout). No check is run for its bugs.

For every other bug, every check runs offline, in a fresh materialization of the **grading view** (the parent's tree
with the fix commit's test files, the official tests), with tests run as
`python -m pytest -p no:randomly -q <ids>` (pytest's cache in `/tmp`, no bytecode):

- (a) the failing tests fail in 3 of 3 runs at the parent's sources and pass in 3 of 3 runs with
  the fix's sources (each set of runs in its own fresh materialization; the runs of a check stop
  once it has failed);
- (b) offline: (a) runs without network; since every check is offline, (a) and (b) are one check,
  reported as "not reproducible offline";
- (c) there are at most 10 failing tests (else "too many failing tests");
- (d) the bug's test files run with the fix's sources in less than 60 s (else "slow tests");
- (e) recordable: the failing tests, recorded with the skill's `pmdb-record` (the round's
  recorder) at the parent's sources, fail under the recorder as they do without it, and the trace
  records functions of the project (else "not recordable": a reproduction recorded by an agent
  would be broken);
- (f) the issue text has at least 80 characters (else "issue too short").

The tests of the test files that pass in both runs of (d) are the tests a fix must not break
(`fix_passed`).

Result (`data/prepared.jsonl`): **16 of 18 bugs eligible**, from 5 projects (click 3, beets 4,
seaborn 1, semantica 4, camel 4); the 2 pipx bugs are excluded (excluded repository). Every
eligible bug passes every check; its test files run in 0.6 to 31 s. With at most 2 bugs per
repository, the selection can take at most 9 exercises (2 + 2 + 1 + 2 + 2).

### Screen (`harness/screen.py`)

Every eligible bug is given once to Sonnet in the study's sandbox (offline, with the API relay),
with only the tools Read, Grep and Glob, the project as in the runs (parent tree, fix's tests
hidden, no environment), and the issue text in the prompt; it is told it can't run anything. A
bug is **localized** if the last component of a function named in its `RESULT:` line (which may
name several, separated by commas, `and` or `/`) is the last component of one of the **fix
functions** (`bugs.fix_functions`, as in round 4). There is no stopping rule.

### Selection (`harness/select_exercises.py`)

As in round 4, with its seed: repositories and each repository's bugs are ordered with a fixed
seed; bugs the screen did not localize ("hard") are taken first, cycling over the repositories
and taking at most 2 bugs per repository, until there are 10; then localized ones ("easy") in the
same way. The pilot bug is the one the rule would take next. **If fewer than 11 bugs are
eligible, every eligible bug is an exercise** (in the order of the rule, then any left by the cap
per repository) and the pilot runs on the first exercise; its runs are excluded from the analysis
as before.

## Arms

- **A (baseline):** the project in `/work`, and Python 3 with the project's dependencies. The
  prompt gives the issue text, says that pdb is installed, that the tests use pytest and that
  there is no network, asks for the root cause and a minimal fix in the project's source code,
  allows adding tests, and asks for a final `RESULT:` line (`harness/prompts.py`).
- **B (pmdb):** the same, plus `/opt/pmdb` (pmdb on `PATH`, the recorder on `PYTHONPATH`), the
  skill as a Claude Code user skill (with the `Skill` tool for it only; bundled skills denied), and
  one sentence in the prompt saying that pmdb is installed with a skill describing how to record
  and query traces. **No trace is recorded in advance.**

## Models and budget

Claude Code 2.1.283 in headless mode on the user's subscription, models `haiku`, `sonnet` and
`opus` (resolved IDs recorded), one run per exercise × arm × model (**60 runs** with 10
exercises, 54 with the 9 the cap per repository allows), plus 2 pilot runs (haiku, both arms, on
the pilot bug) excluded from the analysis. The order of the runs is drawn with round 4's seed.
Runs execute 8 at a time, each capped at 80 turns and 30 minutes; a run interrupted by a usage
limit or an infrastructure error is discarded and run again. After the run, the agent is asked
round 4's feedback questionnaire in the same session.

## Sandbox and the agent's knowledge

As in round 4 (bubblewrap; read-only `/nix`, minimal `/etc`, fresh `$HOME`, writable `/work`,
read-only `/opt/env` and, in arm B, `/opt/pmdb`; git; `--setting-sources user`, no MCP servers,
tools Bash, Read, Edit, Write, Grep and Glob, plus Skill in arm B, pre-approved in `dontAsk`
mode; stdin is `/dev/null`), but **without network** (`harness/offline.py`):

- the sandbox has its own network namespace with only a loopback interface;
- for each run, the host runs `socat UNIX-LISTEN:<root>/api.sock,fork TCP:api.anthropic.com:443`,
  started before the run and stopped after it (and after the feedback turn);
- the socket is bound into the sandbox at `/run/api.sock`, where a second socat forwards
  `127.0.0.1:8443` to it; `/etc/hosts` maps `api.anthropic.com` to `127.0.0.1`, and Claude Code
  gets `ANTHROPIC_BASE_URL=https://api.anthropic.com:8443`, so TLS is verified end to end.

The harness's own test runs and recordings run without the relay. `harness/probe_sandbox.py`
checks that DNS, other hosts and `api.anthropic.com:443` are unreachable, that only the relay
reaches the API, and that the project is imported from `/work`; `harness/skill_check.py` and
`harness/auth_check.py` check the skills and authentication through the relay.

## Measurements

As in round 4. Success is graded on the official tests (`bugs.grade`): the agent's final Python
files that aren't tests are copied over a fresh grading view (the parent's tree with the fix's
test files), and the bug's test files are run offline. A run **succeeds** iff every failing test
passes (`reported_ok`) and every test of `fix_passed` still passes (`regressions = 0`). Tests the
agent wrote or changed don't count. Also recorded: localization (the claimed function against the
fix functions), turns, wall time, tokens, tool calls, pmdb and `pmdb-record` invocations and
failures, the fix's diff against the parent, the files the agent changed, **whether it wrote or
changed tests**, **whether it ran `pmdb-record`** and the traces it left in `/work`, and the
feedback questionnaire.

## Analysis (fixed in advance)

- The paired differences B − A in total tokens and in turns over the exercise × model pairs
  (two-sided Wilcoxon signed-rank test, α = 0.05, median paired difference with a bootstrap 95%
  CI), and success compared with an exact McNemar test (`harness/analyze.py`).
- **Per model**, the same paired differences and success counts (descriptive; with 10 pairs per
  model no test is pre-registered), answering question 1 for each model.
- Descriptive breakdowns by the screen's outcome (hard, easy) and by model, and per exercise the
  screen's outcome next to each arm's success.
- Models: per model and arm, success, localization, tokens, turns, tests written, `pmdb-record`
  and pmdb use and errors (`analyze.py`, `behaviour.py`), and a qualitative comparison of the
  transcripts (`condense.py`): how each model **reproduces** the issue (a test, a script, the
  existing tests) and investigates (reading, running tests, prints, pdb, recording, pmdb
  queries), the mistakes it makes (wrong reproductions, wrong hypotheses, wrong fixes, misuse of
  tools), and the effort that didn't contribute to the fix, with the feedback questionnaires.
- Usability: as in rounds 2 and 4, a thematic summary of the questionnaires and the transcripts
  (`pmdb_attempts.py`): what agents recorded and how, every pmdb error message, queries that
  returned nothing and were reworded, documentation the agents misread, and features they asked
  for, compared with round 4, in particular for the problems fixed since.

## Limitations

- **Memorization.** The bugs were fixed between April and October 2026 and the issues are public;
  agents might recognize a fix. The transcripts are checked for fixes made without investigation.
- **Issues vary in quality.** Some name the faulty function or propose the fix, others only
  describe symptoms. They are used as written.
- **Grading by the upstream tests.** A correct fix that differs from upstream's in behaviour the
  official tests check (an error message, a return value) fails.
- **Fewer bugs and projects.** Requiring a closing issue leaves 18 of round 4's 25 bugs from 6
  projects, and excluding pipx 16 from 5 projects, before the exclusion rules; a few repositories
  contribute most bugs.
- **Same bugs as round 4.** Round 4's results on these bugs are known; the protocol fixes the
  selection mechanically so that they can't steer it.
- **"Hard" is noisy:** the screen makes one attempt per bug.
- **The localization criterion is mechanical:** success is graded by the tests, not by the
  location.

## Changes after the start

None yet.
