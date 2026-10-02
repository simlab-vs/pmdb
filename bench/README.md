# Benchmarks

Studies of how well pmdb helps coding agents debug programs. A study is made of experiments
(rounds). Each experiment lives in its own directory, with a protocol written before any run, its
harness, its exercises, and its results. Finished experiments are never modified; follow-ups go in
new experiments. [RESEARCH_LOG.md](RESEARCH_LOG.md) records what we learned and decided, in order.

```
bench/
  RESEARCH_LOG.md
  lib/pmdbbench/      # code shared by experiments: sandbox, transcripts, statistics, mutation
  usability/
    round-1/          # an experiment: PROTOCOL.md, harness/, programs/, opt-pmdb/, data/, results/
    round-2/
```

| Study | Question | Experiments |
|---|---|---|
| [usability](usability/) | How do agents use pmdb, where do they struggle, and does it change how much effort a fix takes? | [round 1](usability/round-1/) (done 2026-10-01), [round 2](usability/round-2/) (round 1's exercises with the current pmdb and the agent skill) |

## Running an experiment of the usability study

Requirements: Linux with bubblewrap, Python 3, Swift (to build pmdb), Claude Code, and a Claude
subscription token from `claude setup-token`. Save the token to `~/.config/pmdb-study/oauth-token`
with mode 600, in a directory with mode 700.

```
cd bench/usability/round-1
swift build -c release --product pmdb --scratch-path _work/swift-build \
  -Xswiftc -file-prefix-map -Xswiftc "$(git rev-parse --show-toplevel)=/src"
cd harness
python3 assemble.py ../_work/swift-build/release/pmdb ../_work/opt-pmdb  # what agents get in /opt/pmdb
python3 mutate.py > ../_work/mutants.json                 # or reuse ../data/mutants.json
python3 select_exercises.py ../_work/mutants.json > ../_work/exercises.json
python3 probe_sandbox.py                                  # check what agents can see
python3 auth_check.py                                     # check the token works in the sandbox
python3 run_study.py plan && python3 run_study.py run --pilot && python3 run_study.py run
python3 analyze.py > ../results/summary.md
```

Round 2 differs in two steps. It gives agents the skill, so `assemble.py` also takes the skill's
destination, and it reuses round 1's exercises and plan instead of generating them:

```
cd bench/usability/round-2/harness
python3 assemble.py ../_work/swift-build/release/pmdb ../_work/opt-pmdb ../_work/skill
cp ../data/*.json ../_work/
python3 probe_sandbox.py && python3 skill_check.py
python3 run_study.py run --pilot && python3 run_study.py run
```

`_work/` holds builds, sandboxes and raw transcripts and is not committed. Each experiment's inputs
(`data/`) and outputs (`results/`) are committed, including the compressed transcripts.
