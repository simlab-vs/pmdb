# Usability study of pmdb, round 2: report

40 runs (round 1's 10 exercises × 2 arms × 2 models), Claude Code 2.1.283 on the user's
subscription, models `claude-sonnet-5` and `claude-haiku-4-5-20251001`, as in round 1. pmdb, the
recorder and the skill at `7a1d6e7` (see [PROTOCOL.md](../PROTOCOL.md)). The pre-registered
analysis is in [summary.md](summary.md), every pmdb command agents ran is in
[pmdb_attempts.md](pmdb_attempts.md), and the transcripts are in `transcripts.tar.xz`.

## Summary

- **Every run fixed its bug and named the right function**, in both arms, as in round 1 (where one
  pmdb-arm Haiku run failed).
- **pmdb still costs effort on these exercises.** Paired B − A over 20 pairs:
  - tokens: median +57k (95% CI +19k to +127k), Wilcoxon p < 0.001;
  - turns: median +2 (95% CI 0 to +3), p = 0.022;
  - wall time: +11 s (95% CI 0 to +24 s), p = 0.032.

  The exercises are small enough to debug by reading, which agents of both arms did.
- **Sonnet mostly ignored pmdb**:
  - it used pmdb in 2 of its 10 pmdb-arm runs and invoked the skill in the same 2;
  - in round 1 it used pmdb in none;
  - its paired token difference is small (median 154k against 129k).
- **Haiku used the skill and pmdb in every pmdb-arm run.** It invoked the skill on its own, usually
  after reading the program, then ran pmdb about 4 times per run. It also paid for it: median 347k
  tokens against 174k in arm A.
- **Haiku's query errors didn't go down.** 13 of its 41 pmdb commands failed, against 15 of 39 in
  round 1. The causes changed, though: no failure came from the command line (`-e` is gone) or
  from missing features such as `has` or result binding. The remaining errors are misuses that
  the skill describes, but that Haiku made anyway (below).
- **Usefulness ratings rose a little.** Ratings from 1 to 5, arm B, both models:
  - round 2: median 2.5, `[1, 1, 2, 2, 2, 2, 3, 3, 4, 4, 4, 4]`;
  - round 1: median 2, `[1, 2, 2, 2, 2, 3, 3]`.

## Comparison with round 1 (descriptive)

| arm | model | round | success | median tokens (k) | median turns | runs using pmdb | pmdb commands (failed) |
|---|---|---|---|---|---|---|---|
| A | haiku | 1 | 10/10 | 153 | 12 | – | – |
| A | haiku | 2 | 10/10 | 174 | 12.5 | – | – |
| A | sonnet | 1 | 10/10 | 137 | 10 | – | – |
| A | sonnet | 2 | 10/10 | 129 | 9.5 | – | – |
| B | haiku | 1 | 9/10 | 276 | 16.5 | 8 | 39 (15) |
| B | haiku | 2 | 10/10 | 347 | 17 | 10 | 41 (13) |
| B | sonnet | 1 | 10/10 | 147 | 10 | 0 | 0 |
| B | sonnet | 2 | 10/10 | 154 | 8.5 | 2 | 3 (0) |

Arm A moved by up to 14% between rounds with the same exercises, which bounds how much of the
differences in arm B can be attributed to pmdb.

## How agents used pmdb

- **The skill was found and read.** It was invoked in 12 of the 20 pmdb-arm runs (all 10 Haiku
  runs, 2 Sonnet runs), always before the first pmdb command. No agent used `clip`, recorded a
  new trace, or used `__pmdb__`; they all queried the pre-recorded trace.
- **Typical successful use.** List calls of a suspect function with their results (`select
  utilization(...)`, `show $0`), see a wrong result (`call volume_discount_rate(10) -> 0`), then
  read that function. In ex06 the arguments of `busy_intervals` showed a booking past closing
  time, and in ex10 the arguments of `describe` showed a repeated street. Both were the key
  step.
- **Where it didn't help.** In the routing exercises the bug is a tie-breaking or penalty constant
  that shows up as equal costs or arithmetic off by one per left turn. Agents found it by doing
  the arithmetic. Sonnet: "it only confirmed the already-known output". Agents of both arms said
  the code was small enough to read.

## Errors agents hit (13 real failures, all Haiku)

`summary.md` counts 14. The 14th is a false positive: a source excerpt of the calc program
contains `print(f"{number}: error: {e}")`, which the error extractor (inherited from round 1)
mistakes for a pmdb error.

| error | count | cause | covered by the skill? |
|---|---|---|---|
| `expected variable` | 4 | `show query`, `show --query`: `show` takes a variable | yes (`show $N`) |
| `undefined symbol '$1'` | 3 | `show $1` after a single `select` | yes (`$0`, `$1`, … in order) |
| `expected end of command, found '\|'` | 2 | `show $0 \| head -40` inside the heredoc | yes (filters go after the redirection) |
| `expected '…'` | 2 | SQL-like `select /evaluate/ from calls where args[1] like "%%"` | partly (`from` takes a variable) |
| `expected end of command, found '.*'` | 1 | `/subtract/.*\$exception/`: a regex ended early | no |
| `cannot apply == on values of type …` | 1 | `r == -4` where some results are lists | yes (values of different types never compare) |

Agents also asked for better error messages (4 runs), a compact listing of calls and results
(4 runs), local variables inside a call (3 runs), and `head`-like limits inside pmdb (2 runs).

## Findings and suggestions

1. **The skill fixed round 1's documentation problems, not Haiku's carelessness.** Every error
   above but the regex one is covered by the skill, which Haiku had just read. Shorter error
   messages that say what was expected would let agents recover in one step, e.g. `show expects a
   variable such as $0`, or `$1 is not defined; defined variables: $0`.
2. **Bugs visible by reading leave pmdb with nothing to add.** On these exercises the extra cost
   of arm B is mostly Haiku learning the tool. Round 3 tests exercises built to resist reading.
3. **Agents want a compact view.** They asked for `name(args) -> result` without source
   excerpts, and for limits on large outputs. The skill's `grep -v` and `clip` recipes went
   unused, which suggests these belong in pmdb (e.g. `show $0 brief`, `show $0 limit 20`).
4. **State inside a call (local variables, dictionary updates) is out of reach**, by design of
   a call-level trace. The skill could say so up front and suggest `recorder.main.snapshot` for
   values inside a function.

## Limitations

As in round 1:
- one run per condition;
- programs written by Claude;
- model aliases that may change over time.

In addition, the exercises are round 1's, chosen before pmdb's changes, and are mostly easy to
debug by reading. That limits what this round can say about efficiency.
