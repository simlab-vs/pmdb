# Usability study of pmdb, round 4 (protocol)

Written before any agent run. Changes after the first non-pilot run are listed at the end with
their reason.

## Questions

Round 3 (`../round-3/`) was abandoned: a read-only agent localized every mutant of its larger
programs, so mutants can't make exercises that resist reading. This round asks round 2's
questions on **real bugs of real Python projects**, fixed recently:

1. **Usability (primary, qualitative):** how do agents use pmdb and the skill on real projects and
   real bugs, and where do they struggle?
2. **Efficiency (secondary, quantitative):** does access to pmdb change how much effort an agent
   needs to fix a real bug, compared with the same agent without it?
3. **Models (qualitative):** how do Haiku, Sonnet and Opus differ in how they debug (their
   methodology), the mistakes they make, and the effort they waste, with and without pmdb?

## Tool version

pmdb, the Python recorder and the skill `skills/pmdb` at the `ci` commit that adds this protocol
(release build, `_work/swift-build/release/pmdb`, assembled with `harness/assemble.py` into
`_work/opt-pmdb` and `_work/skill`), frozen for the whole round. The commit is recorded in the
results. Usability problems found during the round are reported, not fixed.

## Exercises

### Mining (`harness/mine.py`, done before this protocol; `data/`)

Bugs were mined mechanically; no step looked at the content of a bug.

- **Repositories.** A GitHub search (`language:Python stars:300..20000 pushed:>2026-06-01`,
  not archived or forks; the first 300 results, `data/repos_search.jsonl`) filtered to projects
  with no native sources or compiled build backend, packaging metadata, pytest, and declared test
  dependencies (a test-named dependency group, extra, Poetry/PDM/Hatch group or requirements
  file, or failing that a dev-named one). The 99 accepted repositories were shuffled with a fixed
  seed (`data/repos.jsonl`).
- **Commits.** First-parent commits of the default branch since 2026-03-01 whose message matches
  `fix|fixes|fixed|bug`, changing 1-2 non-test Python source files by at most 15 lines in total,
  and changing at least one runnable test file.
- **Validation.** At the fix commit, the project is installed editable in a fresh uv virtual
  environment (Python 3.14.7) with its test dependencies, **resolved as of the fix commit's date**
  (`uv --exclude-newer`); the changed test files must pass. Then the changed source files are
  restored to the parent commit, and the changed test files must fail within 60 s, without
  errors in setup or collection, and **every failure must be an `AssertionError` whose innermost
  traceback frame inside the project is in a test file** (the assertion rule: the bug shows as a
  wrong value checked by a test, not as an exception raised by the code under test).
- **Stopping.** At most 4 bugs per repository; a repository is abandoned after **3 environment
  failures in a row** (install failure or timeout, or the fixed tests not passing); mining stops
  at 25 bugs from at least 8 repositories, or after **400 validation attempts** (the cap counts
  commits that reach validation, not every commit examined).

Mining visited 20 repositories, examined 383 commits, attempted 80 validations and validated
25 bugs from 9 repositories (`data/bugs.jsonl`, `data/mining_log.jsonl`), fixed between
2026-04-24 and 2026-10-01.

### The agent's view (`harness/bugs.py`)

- `/work`: the project at the fix commit, without `.git`, caches and build artifacts, with every
  file changed by the fix that isn't a test restored to its parent version (the source files,
  but also changelogs and documentation, which would describe the fix). The fixed tests are kept.
- `/opt/env` (read-only, first on `PATH`): a copy of the bug's environment, in which the editable
  install points at `/work`. No file in it mentions the host's paths.
- No network for tests: the prompt asks the agent not to use it, and the harness runs every test
  offline.

### Exclusion rules (`harness/prepare.py`, pre-registered; `data/prepared.jsonl`)

In the sandbox, with tests run as the prompt says (`python -m pytest -p no:randomly -q <ids>`,
with pytest's cache in `/tmp` and no bytecode so that the harness doesn't write in `/work`):

- (a) the failing tests fail in 3 of 3 runs at the parent's sources and pass in 3 of 3 runs with
  the fix's sources (else "not reproducible");
- (b) the same holds with the network unshared (else "needs network");
- (c) there are at most 10 failing tests (else "too many failing tests");
- (d) the bug's test files run offline with the fix's sources in less than 60 s (else "slow
  tests");
- (e) the failing tests can be recorded as for arm B: under the skill's `pmdb-record`, at the
  parent's sources, they fail as they do without it, and the trace records functions of the
  project (else "not recordable"; otherwise arm B would get a broken trace). This rule was added
  after the first preparation showed that the recorder breaks some projects' tests (an infinite
  recursion in the recorder for camel, a broken fixture for one beets bug), before any run.

The tests of the test files that pass in two offline runs with the fix's sources are the tests a
fix must not break (`fix_passed`).

Result: see `data/prepared.jsonl` and the results. A first preparation, without git on the
sandbox's `PATH` and without rule (e), found 22 of 25 bugs eligible (`_work/prepared.before-git.jsonl`
is not committed); it was re-run after git was added, since pipx's fixtures require it.

### Screen (`harness/screen.py`)

Every eligible bug is given once to Sonnet in the study's sandbox, with only the tools Read, Grep
and Glob, the project as in the runs, and `/work/failing_tests.txt` holding pytest's output for
the failing tests at the parent (captured by `prepare.py`). The prompt is the study's, saying
which tests fail and that it can't run anything. A bug is **localized** if the last component of
a function named in its `RESULT:` line (which may name several, separated by commas, `and` or
`/`) is the last component of one of the **fix functions**: the
functions or methods of the parent's source files that enclose the lines changed by the fix
(`bugs.fix_functions`; lines in a class body outside methods count as the class, and a fix with
no change inside a function counts as `<module>`). There is no stopping rule.

The screen was first run on the 22 bugs of the first preparation. It localized 20, and one of
the 2 others (semantica-e4fafc2) named the three fix functions in one comma-separated claim,
which the rule then compared as a single name; the rule was corrected as above before any run.
Bugs that become eligible in the second preparation are screened in the same way. A bug whose
failing tests' output changes in substance in the second preparation would be screened again;
the outputs only differed by ports, times, temporary paths and the order of fields in printed
objects, so no bug was screened again.

### Selection (`harness/select_exercises.py`)

Repositories and each repository's bugs are ordered with a fixed seed. Bugs the screen did not
localize ("hard") are taken first, cycling over the repositories and taking at most 2 bugs per
repository, until there are 10; then localized ones ("easy") in the same way. The pilot bug is
the one the rule would take next. If fewer than 10 bugs are eligible, all are used.

## Arms

As in round 2:

- **A (baseline):** the project in `/work`, and Python 3 with the project's dependencies. The
  prompt names the failing tests and the command the user ran, asks for a fix of the root cause in
  the project's source code, not in the tests, and asks not to use the network.
- **B (pmdb):** the same, plus `/opt/pmdb` (pmdb on `PATH`, the recorder on `PYTHONPATH`), the
  skill as a Claude Code user skill (with the `Skill` tool for it only; bundled skills denied), a
  trace of the failing tests recorded in advance at `/work/report.pmdb`, and one sentence in the
  prompt saying so.

The trace is recorded with the skill's `pmdb-record`, with the network (pipx's fixtures download
a package cache, as they do when agents run the tests), run by the environment's Python on
a driver script that calls `pytest.main` on the failing tests. The driver is written, for the
recording only, in the directory from which the project's packages are imported (`/work` or
`/work/src`), because `pmdb-record` instruments the Python files of its script's directory; it
is deleted afterwards, as is anything else the tests wrote in `/work`. `run_study.py` checks that
the trace records functions of the project and notes whether it records the fix functions.

## Models and budget

Claude Code 2.1.283 in headless mode on the user's subscription, models `haiku`, `sonnet` and
`opus` (resolved IDs recorded; `opus` resolves to `claude-opus-5-5`), one run per exercise × arm ×
model, **60 runs**, plus 2 pilot runs (haiku, both arms, on the pilot bug) excluded from the
analysis. The order of the runs is
drawn with round 2's seed. Runs execute two at a time, each capped at 60 turns and 20 minutes; a
run interrupted by a usage limit or an infrastructure error is discarded and run again.

## Sandbox and the agent's knowledge

As in round 2 (bubblewrap; read-only `/nix`, minimal `/etc`, fresh `$HOME`, writable `/work`,
read-only `/opt/pmdb` in arm B; `--setting-sources user`, no MCP servers, tools Bash, Read,
Edit, Write, Grep and Glob, plus Skill in arm B, pre-approved in `dontAsk` mode), plus the
read-only `/opt/env`, the library path its wheels need, and git (some projects' tests need it). Claude Code itself needs the network,
so the sandbox of the runs keeps it; only the harness's test runs are offline.
`harness/probe_sandbox.py` and `harness/skill_check.py` check the sandbox and the skills before
the runs.

## Measurements

Those of round 2, with success defined on the bug's tests (`bugs.grade`): the agent's final
Python files that aren't tests are copied over a fresh copy of the project, and the bug's test
files are run offline. A run **succeeds** iff every failing test passes (`reported_ok`) and every
test of `fix_passed` still passes (`regressions = 0`). Edits to tests don't count. Also recorded:
localization (the claimed function against the fix functions), turns, wall time, tokens, tool
calls, pmdb and `pmdb-record` invocations and failures, the fix's diff against the parent, the
trace's size and whether it records the fix functions, and the feedback questionnaire.

## Analysis (fixed in advance)

- The paired differences B − A in total tokens and in turns over the exercise × model pairs
  (two-sided Wilcoxon signed-rank test, α = 0.05, median paired difference with a bootstrap 95%
  CI), and success compared with an exact McNemar test (`harness/analyze.py`).
- Descriptive breakdowns by the screen's outcome (hard, easy) and by model, and per exercise the
  screen's outcome next to each arm's success.
- Models: per model and arm, success, localization, tokens, turns and pmdb errors
  (descriptive), and a qualitative comparison of the transcripts: how each model investigates
  (reading, running tests, prints, pdb, pmdb queries), the mistakes it makes (wrong hypotheses,
  wrong fixes, misuse of tools), and the effort that didn't contribute to the fix, with the
  feedback questionnaires.
- Usability: as in round 2, a thematic summary of the questionnaires and the transcripts: every
  pmdb error message, queries that returned nothing and were reworded, documentation the agents
  misread, and features they asked for, compared with rounds 1 and 2.

## Limitations

- **Memorization.** Bugs were fixed between 2026-03 and 2026-10, so the fixes may be in the
  models' training data. Agents might recognize a fix rather than debug; the transcripts are
  checked for fixes made without investigation.
- **Projects of very different sizes**, from about 5k to 200k non-blank source lines, and a few
  repositories contribute most bugs. With at most 2 bugs per repository, effects specific to a
  project weigh on the results.
- **The tests describe the bug.** The fixed tests name the expected behaviour, often more
  precisely than a user's report would.
- **"Hard" is noisy:** the screen makes one attempt per bug, and reading the failing test's output
  is more than round 3's screen had.
- **The localization criterion is mechanical:** a fix may change several functions, or a correct
  fix may be elsewhere than the upstream one; success is graded by the tests, not by the
  location.

## Changes after the start

None.
