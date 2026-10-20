# Usability study of pmdb, round 5: report

54 runs on reported issues: 9 real bugs from 5 Python projects (beets, click, seaborn, semantica,
camel) × 2 arms × 3 models (`claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5-5`),
Claude Code 2.1.283. pmdb, the recorder and the skill are at `2777a5d`.

What changed from round 4 (see [PROTOCOL.md](../PROTOCOL.md)):
- **The prompt is the GitHub issue the fix closes, not the failing tests.** The project is at the
  parent commit, so the official tests are hidden; they grade the fix.
- **Agents have no network.** Claude Code reaches only the API, through a relay.
- **Arm B gets no pre-recorded trace.** pmdb, its recorder and the skill are installed, and the
  prompt says so.

Supporting files:
- [summary.md](summary.md): the pre-registered analysis;
- [behaviour.md](behaviour.md): how agents worked;
- [pmdb_attempts.md](pmdb_attempts.md): every pmdb command;
- `transcripts.tar.xz`: the transcripts.

## Summary

- **Agents didn't use pmdb.**
  - The skill was invoked in 3 of the 27 pmdb-arm runs (Haiku twice, Sonnet once).
  - pmdb was run in 1 run (Haiku: 1 recording, 6 queries, 3 failed).
  - Sonnet and Opus never ran it.
  - Without a trace pointing at it, the agents reproduced bugs with tests and prints, and pmdb
    didn't occur to them. The round therefore measures adoption, not value: the arms differ only
    by an unused tool.
- **No difference between arms**, as expected given non-use. Success A 12/27, B 13/27. B − A:
  median +58k tokens (p = 0.41), +0 turns (p = 0.81).
- **The task is much harder than round 4's.** 25 of 54 runs succeeded, against 59 of 60. The
  models' costs differ as in round 4:

  | Model | Median tokens | Median turns |
  |---|---|---|
  | Opus | 144k | 12 |
  | Sonnet | 1.8M | 48 |
  | Haiku | 1.6M | 38 |

  Every model wrote tests in almost every run.
- **The grading is confounded by specification gaps.** Four exercises (ex01, ex02, ex06, ex09)
  were solved by no run of any model or arm, and ex04 by one. In the runs inspected, agents
  fixed the reported behaviour in the right function. The official tests, though, check
  implementation choices the issue doesn't state. In ex09, a list must be wrapped under the
  exact key `"__camel_tool_result__"`.
  - Success on these exercises measures whether an agent guessed the upstream design.
  - Of the remaining 5 exercises, 4 were solved by all 6 runs (ex03, ex05, ex07, ex08).

## Per exercise

Each cell is model and arm (h = Haiku, s = Sonnet, o = Opus). ✓/✗ is success; `?` means the
claimed function isn't one of the fix's functions.

| exercise | hA | hB | sA | sB | oA | oB |
|---|---|---|---|---|---|---|
| ex01 semantica (hard) | ✗? | ✗ | ✗ | ✗? | ✗ | ✗ |
| ex02 beets (hard) | ✗? | ✗? | ✗? | ✗? | ✗? | ✗? |
| ex03 beets (hard) | ✓? | ✓ | ✓? | ✓? | ✓ | ✓ |
| ex04 click | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| ex05 seaborn | ✓ | ✓ | ✓? | ✓ | ✓ | ✓? |
| ex06 semantica | ✗? | ✗? | ✗? | ✗? | ✗? | ✗? |
| ex07 camel | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ex08 click | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ex09 camel | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Feedback

- **pmdb:** the 2 usefulness ratings are 1 and 2.
- **What agents wanted:**
  - context: git history or the referenced PRs;
  - error text instead of screenshots;
  - offline data, e.g. seaborn's example datasets;
  - a call graph or the call sites of a function;
  - a way to emulate platform-specific behaviour (Windows file locking);
  - an offline stub for an external API.
- Several said the issue was precise enough that reading sufficed.

## Problems in the harness

- **A false interruption stopped the runner.** It treated a run that reached the 80-turn cap as
  interrupted by a usage limit, because a number in the raw transcript contained `529`, and
  stopped after 17 runs. Fixed and recorded in the protocol; the discarded run was re-run.
- **Grading by official tests requires the issue to specify what they check.** No step of the
  selection checked this, so about half the exercises can't be solved as stated.

## What this means

1. **Adoption is the first obstacle when nothing points to pmdb.** The skill's description asks
   agents to skip it when reading suffices, and agents judged that it did, even on exercises
   they then failed. Measuring pmdb's value needs either a setting where its use is natural (a
   trace that comes with the report, as in round 4's post-mortem framing) or an arm told to use
   it.
2. **Issue-based exercises need a solvability check.** For example, a reference fix written
   from the issue alone must pass the official tests, or the grade must be limited to the
   behaviour the issue describes.
3. **The models' gap dwarfs the tool's.** Opus fixes with about a tenth of Sonnet's and Haiku's
   tokens.
