# Benchmarks

Studies of how well pmdb helps coding agents debug programs. Each study lives in its own
directory, with a protocol written before any run, the harness, the exercises and the results.
[RESEARCH_LOG.md](RESEARCH_LOG.md) records what we learned and decided, in order.

| Study | Question | Status |
|---|---|---|
| [usability](usability/) | How do agents use pmdb, where do they struggle, and does it change how much effort a fix takes? | Round 1 done (2026-10-01) |

## Running the usability study

Requirements: Linux with bubblewrap, Python 3, Swift (to build pmdb), Claude Code, and a Claude
subscription token from `claude setup-token`. Save the token to `~/.config/pmdb-study/oauth-token`
with mode 600, in a directory with mode 700.

```
cd bench/usability
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

`_work/` holds builds, sandboxes and raw transcripts and is not committed. Each round's inputs
(`data/`) and outputs (`results/`) are committed, including the compressed transcripts.
