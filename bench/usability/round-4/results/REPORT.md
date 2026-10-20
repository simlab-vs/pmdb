# Usability study of pmdb, round 4: report

60 runs on real bugs: 10 bugs from 7 Python projects (beets, click, pipx, semantica, seaborn,
needle, Gymnasium), fixed upstream between April and September 2026, × 2 arms × 3 models. The setup:
- Claude Code 2.1.283 on the user's subscription;
- models `claude-haiku-4-5-20251001`, `claude-sonnet-5` and `claude-opus-5-5`;
- pmdb with the value semantics of `c01502c`, and the skill as committed in `3cfe7c9`.

The protocol, with its changes after the start, is in [PROTOCOL.md](../PROTOCOL.md). Supporting
files:
- [summary.md](summary.md): the pre-registered analysis;
- [behaviour.md](behaviour.md): how agents worked, per run;
- [pmdb_attempts.md](pmdb_attempts.md): every pmdb command;
- `transcripts.tar.xz`: the transcripts.

## Summary

- **pmdb didn't make agents more efficient, for any model.** All runs but one fixed their bug
  (A 29/30, B 30/30). Over 30 exercise × model pairs, B − A:
  - tokens: median +76k (95% CI +22k to +212k), Wilcoxon p = 0.08;
  - turns: median +2 (95% CI 0 to +5), p = 0.36.
- **The exercises were easy.** A read-only Sonnet screen localized 20 of the 22 eligible bugs
  without running anything. The fixed tests state the cause in their names, docstrings or
  comments (e.g. "the `f.close()` … sits after the `yield`"). Agents in both arms read the
  failing test, then the function it pointed to, and fixed it.
- **The models differ far more than the arms.** Medians per run, with pmdb in parentheses:

  | model | fixed | tokens | turns | used pmdb (runs) | pmdb commands failed |
  |---|---|---|---|---|---|
  | Haiku | 9/10 (10/10) | 536k (829k) | 21 (28) | 10/10 | 22 of 59 |
  | Sonnet | 10/10 (10/10) | 376k (501k) | 16 (18) | 4/10 | 4 of 19 |
  | Opus | 10/10 (10/10) | 51k (70k) | 6.5 (6) | 2/10 | 0 of 2 |

- **pmdb helped when the tests couldn't be run.** In the pipx exercises the tests hung or took
  minutes. The trace was then the only runtime evidence, and agents used it to see that
  `reinstall` returned an error outcome instead of raising (Sonnet, Haiku and Opus). This is
  the post-mortem setting pmdb is built for, and it's what the next round should target.

## How the models debug

Each model's 20 transcripts (both arms) were analyzed separately. Quotes and run ids are in the
analysis notes summarized here.

### Methodology

- **Opus.** 3–6 tool calls per run, first edit at step 2–5. The first call bundles running the
  failing test (`| tail`), grepping the suspect `def`, and grepping the test body, in one shell
  command. It then reads one or two regions with `sed -n`, makes one edit (multi-site edits as
  small Python scripts with `assert s.count(old) == 2`), and runs the whole test file. Every
  first edit was its final fix. With pmdb available it says "Let me look at the code directly
  first", and it followed the skill's own advice to skip pmdb "when the code is small enough to
  check by reading" in 8 of 10 runs.
- **Sonnet.** Runs the failing test, greps the function named in the assertion, reads it, edits,
  re-runs, then runs a wider suite (median 16 steps). It reached for runtime probes (monkeypatch
  scripts, debug prints, `faulthandler`) only when reading wasn't enough. In arm B it loaded the
  skill in 5 runs and queried the trace in 4, always *after* forming a hypothesis ("Let me verify
  with pmdb before fixing"); pmdb never led it to the bug.
- **Haiku.** Starts with orientation (`ls`, `find`, Reading directories), runs the test, reads the
  test, greps, reads, edits, then re-runs and re-reads repeatedly (median 21 steps). In arm B it
  invoked the skill first in all 10 runs and queried the trace before running the tests, ad hoc
  rather than to test a hypothesis; in 5 runs it edited before seeing the test fail. It never
  used pdb, although the prompt offers it.

### Mistakes

- **Opus:** no wrong hypothesis or wrong first fix. Its mistakes were operational: misjudging
  slow tests as hung and killing them, `pkill -f` patterns that matched its own shell, and once
  naming a function without reading its `def` line.
- **Sonnet:** two incomplete first fixes (ex06 broke a sibling test; ex05 patched the caller
  instead of the function), wrong path guesses, Grep tool misuse, and claims that tests passed
  based on empty output. pmdb mistakes: `show report.pmdb` instead of `show $0`, exact names
  for methods (`get_tracks_from_medium(...)` misses `MusicBrainzPlugin.get_tracks_from_medium`),
  regexes that didn't match the whole name.
- **Haiku:** the same wrong first fixes in both arms for ex06 and ex07 (a deterministic prior),
  and **edits driven by pmdb**: `select _(...) raised e` returned hundreds of exceptions that
  Python and the libraries raise and catch routinely (`__getattr__` probes, logging), and Haiku
  "fixed" them in 3 runs, once reporting one as the root cause. Its 22 failed pmdb commands:
  - pipes inside the heredoc, 9: `show $0 | head`;
  - `show <file>` instead of `show $0`, 5;
  - a pmdb command that doesn't exist: `python3 -m pmdb`, `<skill>/scripts/pmdb`;
  - dotted names without a regex;
  - `...` mixed with other patterns;
  - SQL-like `like`.

### Wasted effort

- **Opus:** little. The exceptions were seaborn's 6-minute regression suite polled with `sleep`
  (one arm-B run hit the 20-minute limit while sleeping, after fixing the bug), and attempts to
  download a pristine copy of the package to compare.
- **Sonnet:** environment hangs dominated (pipx fixtures downloading packages: up to 35 of 46
  steps), plus long polling after the fix in seaborn. With pmdb, ex01 took 31 turns and 1,172k
  tokens against 17 turns and 419k without, on queries of a trace that was broken (see below).
- **Haiku:** orientation steps at the start, 4–5 steps after the tests passed (re-running and
  re-reading), and in arm B 4–12 steps finding out how to run pmdb plus the red-herring
  exceptions.

### Feedback

- **pmdb usefulness (1–5, arm B):**
  - Haiku: 2, 2, 3, 4, 4, 4, 5 (the 5 came from a run that pmdb misled);
  - Sonnet: 1, 2, 3, 3;
  - Opus: 3.
- **Wishes, across models:**
  - pipes or `head` inside pmdb;
  - error messages that name what is expected;
  - a list of the recorded functions with call counts;
  - a hint when a name matches nothing (e.g. that the method is `Class.method`);
  - exceptions grouped or deduplicated;
  - dataclasses recorded as tables without `__pmdb__`;
  - selecting fields of the results to show.

## Problems in pmdb found by this round

1. **The recorder recursed forever** when encoding a value called recorded code (camel: a
   property read by `isinstance`). This excluded all 4 camel bugs. **Fixed** in `fbe6e19`: calls
   made while values are encoded aren't recorded.
2. **The recorder breaks some tests:**
   - beets-38669c8: a fixture failed under `pmdb-record`, so the bug was excluded;
   - ex01 (beets-d91df40): the test raised a different error under the recorder, so its
     pre-recorded trace only covered setup. Sonnet ran 6 empty queries on it.

   Not yet diagnosed.
3. **`raised` matches routinely caught exceptions.** Correct by definition, but the skill's
   recipe `select _(...) raised e` invites it. The skill should say so, and pmdb could tell
   exceptions that propagated out of a test from those caught along the way.
4. **Name matching.** Methods are recorded as `Class.method`, and agents of every model wrote the
   bare method name, which silently matched nothing.
5. **Errors and messages.**
   - A missing trace file gives "The operation could not be completed. The file doesn't exist."
     without the file name.
   - `show <path>` gives "expected variable".
   - An empty result doesn't say whether the function was recorded at all.
6. **Opaque values.** Results that are objects print as `<object>`, e.g. pipx's
   `OperationResult` and Gymnasium spaces.

## Problems in the harness (fixed or to fix next round)

- **Network.** The sandbox shares the network because Claude Code needs it. Despite "Don't use
  the network", agents ran `pip download` (Sonnet, Opus) and `pip install pmdb` (Haiku), and
  pipx's fixtures download packages. **Next round:** run Claude Code without network, through a
  proxy that only reaches the API.
- **Grading of pipx.** Its tests need a package cache downloaded at the start, and fail offline.
  `prepare.py`'s offline check had passed only because it reused the cache of its online runs, so
  every pipx run was first graded as a failure. The 12 pipx runs were graded again with the
  network (`harness/regrade.py`; the offline grades are kept as `grade_offline`).
- **Sixteen runs on 14 cores** inflated wall times; two seaborn runs hit the 20-minute limit
  while waiting for their test suites, after fixing the bug.

## What this means for the next round

These exercises give the cause away in the tests, which favours reading, and Opus in particular
needs no runtime evidence. pmdb should be evaluated where runtime evidence is needed and hard to
get otherwise:

1. **Issues instead of tests**, at the user's suggestion. The prompt is the issue a user reported,
   the fixed tests are hidden, and the agent reproduces, diagnoses and fixes; the official tests
   grade the fix. In arm B the agent records its own reproduction.
2. **Post-mortem runs that can't be replayed**: the agent gets the code, the failure report and
   (in arm B) the trace, but not the input or the environment that produced the failure.
3. **Performance bugs** (also the user's suggestion): if pmdb records each call's duration, it
   can answer questions a profiler can't, such as which arguments make a function slow,
   repeated calls with identical arguments, or calls whose duration grows faster than their
   input.
