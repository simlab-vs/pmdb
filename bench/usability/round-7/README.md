# Usability study of pmdb, round 7 (exploratory): post-mortems of runs that can't be replayed

**These scenarios were designed to favour runtime evidence.** Round 6 found that pmdb made a difference in only
one of six designed scenarios: `refund-postmortem`, the only one whose failing input the agent couldn't get. In the
others the input was in `/work` and the run was fast, so agents wrote scripts against the program's modules and
didn't need a trace. Round 7 therefore studies only the post-mortem setting. A production run went wrong, and it
can't be replayed. The agent gets:
- the code;
- the issue: what the user saw, the wrong numbers and the expected ones;
- the run's INFO log and the reports the job wrote, inside `work/`.

It is an existence test of whether a handed-over trace helps in this setting, not an unbiased estimate of how often
pmdb helps on real bugs. The bugs, data and issues were hand-crafted to make reading alone expensive.

## Arms

- **Both arms** get `work/` (as `/work`) and `issue.md`. They may run the program on inputs they write themselves.
  Every program documents its input format, and two accept offline inputs: a levels file, a queue spool.
- **Arm B** also gets pmdb, the pmdb skill and `/work/report.pmdb`, a trace of the failing run recorded by the
  scenario's `record.sh`.

## Scenarios (`scenarios/<name>/`)

The four new scenarios differ in why the run can't be replayed.

| # | Why it can't be replayed | Name | Program | Bug | Decisive pmdb query |
|---|---|---|---|---|---|
| 1 | **Private data:** the HR export was deleted after the run | `payroll-postmortem` | September payroll, 650 persons, salaried and hourly; 1,103 lines in 18 modules | An employment runs from the first contract row's start to the last row's end, and the day-rate lookup doesn't check a row's end. Gap days between contracts are paid: base salaries +€16,904.43, meal allowances +€502.50, for 9 persons | `select segment_at(segments, day) -> s where s.valid_to != none`, then `export` and `query.py`: lookups past the row's end, by person |
| 2 | **External state:** the inventory service's levels have changed since | `stock-allocation` | Nightly order allocation, 5,123 lines, 4 warehouses, 3 channels; 1,012 lines in 13 modules | For marketplace lines, the free stock is the available stock minus safety stock and can be negative. `if take:` books the negative pick, which creates phantom stock and over-allocates the next warehouse. Result: short picks (Leipzig 127, Rotterdam 82) and 335 units over-shipped | `select allocate_line(l) -> a where a.picks.any(p => p.qty < 0)`, then `export` |
| 3 | **Clock:** the run crossed midnight, on a live database that has moved on | `points-expiry` | Loyalty-points nightly job with the month-end expiry; 1,188 lines in 14 modules | The business date is fixed at start, but `due_lots` defaults to `clock.today()`. 1,842 members processed after midnight get October's cutoff: 742,058 points expired instead of 468,705 | `export` the `ExpiryPolicy.cutoff_for` and `due_lots` calls; `query.py` shows the cutoff date change mid-run |
| 4 | **Consumed queue:** the messages were deleted as they were posted | `card-ledger-queue` | Prepaid-card ledger draining an unordered, at-least-once queue; 1,084 lines in 16 modules | Processor re-sends are recognised by a fingerprint of transaction fields that omits `network_ref`. Identical offline fares (no auth code, date-only time) collide: 280 clearings, €808.30 not posted | `select classify(m) -> "resend" where m.event_type == "clearing"`, plus the posted ones, exported; `query.py`: dropped clearings whose `network_ref` was never posted |
| 5 | **Private data** (round 6, copied unchanged) | `refund-postmortem` | Payout reconciliation; 816 lines | NovaPay refund lifecycle events are each booked as a refund | `select /Ledger\.apply_refund/(_, _, t) where t.status != "succeeded"` |

Scenario 5 is round 6's `refund-postmortem`, copied byte for byte. Its oracle never needed `patch`, since it runs
the agent's job on committed hidden exports, so nothing had to change. Its `validate.sh` still defaults `PMDB` to
round 5's build; `validate_all.sh` sets `PMDB` to the build with `export`.

Each scenario directory holds:
- `work/`: what the agent sees, including the failing run's log and reports;
- `issue.md`: the symptom, the expected figures and why the run can't be repeated;
- `fix.patch`: the reference fix (`patch -p1 -d <dir>`), one line in scenarios 2–4;
- `wrong-fix*.patch`: plausible incomplete fixes, which the oracle must fail;
- `oracle.py <dir>`: hidden inputs or states (the original plus new ones and a regression case), with truth
  computed independently by the generators. It needs only python3, and exits 0 for pass;
- `record.sh [WORKDIR]`: writes `WORKDIR/report.pmdb` and nothing else;
- `query.pmdb`, with `query.py` (aggregation over exported JSONL) and `query_expect.txt`;
- `notes.md`: the design, why the code and log aren't enough, arm A's route, how the trace shortens it, fairness
  threats, timings and how to regenerate the data;
- `validate.sh`;
- `gen/`: the generators;
- `hidden/`: the oracle's data;
- `private/`: the input or state the agent never sees;
- `sim/` in `points-expiry` only: a `sitecustomize.py` that simulates the clock for recording, validation and the
  oracle.

## Validation

`validate_all.sh` runs every scenario's `validate.sh`, and all five pass. Each one checks that:
- the failing run on the private data reproduces the issue's figures and the log and reports in `work/`;
- the oracle fails the pristine code;
- the fix applies, gives the expected figures and passes the oracle;
- each `wrong-fix*.patch` fails the oracle;
- `record.sh` writes only the trace;
- the query output contains `query_expect.txt`.

| scenario | trace | observations | recording | decisive query (debug pmdb) | validate.sh |
|---|---|---|---|---|---|
| payroll-postmortem | 42 MB | 300k | 4 s | about 13 s with loading | 12 s |
| stock-allocation | 36–42 MB | 249k | 6 s | about 7 s | 12 s |
| points-expiry | 76 MB | 336k | 19–40 s | about 32 s | 154 s (oracle about 30 s) |
| card-ledger-queue | 50 MB | 308k | 6 s | about 8 s | 17 s |
| refund-postmortem | 49 MB | 317k | 14–24 s | 20–40 s | 26 s |

## Arm A must not be hopeless

Each bug can be found from the code, the log and careful reasoning, or with inputs the agent writes itself. Each
`notes.md` describes that route. The leads are:
1. **payroll:** the allowance difference is a whole number of €7.50 days, which points at extra employed days, and
   `employment_for` checks for overlaps but not for gaps.
2. **stock-allocation:** all over-shipped orders are marketplace orders, the README states the safety-stock rule, and
   the orders are available with a `--levels-file` option.
3. **points-expiry:** the log shows the run crossing midnight, and the issue shows an "expiring 2026-10-31" shortfall.
4. **card-ledger-queue:** `messages.py` documents that offline transactions have no auth code, and two identical
   fares are easy to write into a spool.

## Known weaknesses (details in each `notes.md`)

- **The leads above may make arm A cheap.** The threat is largest in stock-allocation, where arm A can replay with
  invented levels, and in points-expiry, where the midnight crossing is visible in the log.
- **Domain knowledge** may let a model guess the bug: contract gaps, offline transit clearings, refund lifecycles.
- **The clock is simulated in points-expiry.** It patches `time` and `datetime` through `sitecustomize`, so a fix
  that reads the date some other way would be misgraded. At the simulated pace every month-end run would cross
  midnight; the code gives no reason why August's didn't.
- **One issue was edited for hints:** a sentence about low stock after a sale was removed from stock-allocation's
  issue.
- **The code was shaped for the recorder,** as in round 6: dicts and NamedTuples, cheap `self`, generator pipelines.
- **The traces contain the private data.** That is the premise: post-mortem traces are recorded in production.
- **Reading resistance was not screened** with pilot runs.
