# points-expiry: notes

**Kind:** time-dependent post-mortem. A month-end run's outcome depended on the wall clock *during* the run. The agent
knows when the run started: cron at 23:50, and the log is timestamped. But the database state at that time is gone,
and the clock readings during the run can't be replayed exactly. The agent gets the code, the job's INFO log, the
reports and the issue with the audit's figures. Arm B also gets `report.pmdb`, a trace of that run.

## The program (`work/`, 1,188 lines of Python in 14 modules, plus config, log and reports)

`nightly.py` is the nightly job of a loyalty programme. It works on a live SQLite points database (members, lots,
pending activity, ledger, job runs):
- **Every night** it posts the day's earn/burn/adjust records (`posting.py`). It applies tier multipliers, and burns
  take points from the lots that expire soonest.
- **On the last day of a month** it runs the month-end stage, batch by batch (`expiry.py`, `statements.py`,
  `crm.py`):
  - expires the lots due under the terms and conditions (`policy.py`): purchase and goodwill points at the end of
    the 12th month after earning, promo points at the end of the 3rd;
  - forfeits closed accounts;
  - pushes each open account's statement to the CRM, one HTTP request each.
- **Every night** it writes a JSON/text report with the points liability for finance (`liability.py`, `report.py`).

The other modules are the clock (`clock.py`), ISO-date arithmetic (`dates.py`), settings, store, audit stamps and
checks.

## The bug

`run()` decides the business date and the mode **once**, at start: `business_date = clock.today()`, `month-end` iff
it is the month's last day. The business date is passed down as `posted_on`. But `expire_member` asks the policy
`policy.due_lots(lots)` without it:

```python
    def due_lots(self, lots, on=None):
        """Lots whose points expire at the end of the month containing ``on`` (default: today)."""
        on = on or clock.today()
        cutoffs = {source: self.cutoff_for(source, on) for source in self.months_by_source}
```

**The Sept 30 run.** It started at 23:50:02 CEST and, with the slow CRM, finished at 00:06:13 on Oct 1. About
2,700 of 4,800 members were processed before midnight, with the cutoffs of Sept 30:
- purchase and goodwill points: earned before 2025-10-01;
- promo points: earned before 2026-07-01.

The remaining 1,842 non-exempt members got the cutoffs of Oct 1: 2025-11-01 and 2026-08-01. Their October 2025
purchase/goodwill lots and July 2026 promo lots expired a month early:
- 273,353 points too many expired: 742,058 instead of 468,705;
- the liability is EUR 1,120.75 too low;
- the "expiring 2026-10-31" forecast is 273,353 too low.

Posting, forfeiture, statements and the other figures are right.

**Fix** (`fix.patch`, one line in `loyalty/expiry.py`): `policy.due_lots(lots, posted_on)`. Equivalent fixes pass,
e.g. freezing the business date in `clock`, or passing the date through some other way.

## Why the faulty code looks right

- `due_lots` has a documented default, "today", reasonable for a policy object that the app back end could also ask.
- `expire_member` passes `posted_on` to every booking. Leaving it out of the `due_lots` call reads as "the lots due
  now", which is what a nightly job means.
- The cutoff arithmetic in `cutoff_for` is correct, and is where a reader told "expired too early" will look first.
- The code reads the clock in many harmless places:
  - audit stamps on every booking;
  - the CRM request time;
  - the statement's `generated_at`;
  - the run's start and finish;
  - log lines.

  `clock.today()` is called only twice, in `run()` and in `due_lots`. That gives a careful grep a chance.
- The mode is decided once at start, so there is no visible "month-end check" that fails after midnight. Only the
  date that is read again does.

## Why code and log alone don't suffice (and why arm A is not hopeless)

The issue says "too many expired", gives the audit's figures and complaints that points "weren't due yet". It
doesn't name the earning month. The agent has no database to run on. The log's facts, if it notices them:
- the run started at 23:50:02 and ended at 00:06:13 the next day;
- batch 12 of 20 finished just after midnight;
- the "expiring 2026-10-31" forecast is far below the audit's.

**What a strong reader would likely try first:**
- the cutoff arithmetic (`1 - months`), the obvious place for "a month too early". It is correct. Changing it
  (`wrong-fix.patch`, `-months`) fails the oracle on every month end, h3 included;
- burns' lot order;
- promo months;
- platinum exemption;
- forfeiture;
- the tier multiplier;
- end-of-month clamping in `add_months`.

**A concrete arm-A route:**
1. Notice in the log that the run crossed midnight.
2. Grep `clock.` / `today()` and find the default in `due_lots`.
3. Or write a small synthetic database (the schema is in `store.py`) and run the job with a monkeypatched
   `clock.today`/`time.time` that crosses midnight. Then see Oct 2025 lots expire for later members.

Each step is ordinary debugging, but the agent has to form the time hypothesis without data. "Expired too early"
pulls toward the arithmetic, and nothing shows how many members were affected or which lots. We estimate 10–25 turns
for a strong reader who notices the timestamps, and possibly a wrong cutoff "fix" for one who doesn't.

## How the trace shortens it

The trace has every policy call with its arguments and results; dates are ISO strings. A natural route from the
issue, without knowing the bug:
1. `show functions`: `ExpiryPolicy.due_lots` 4,318 calls, `ExpiryPolicy.cutoff_for` 12,954, `today` 4,319.
2. Look at what expired (`due_lots`' results) or at the cutoffs. `query.pmdb` exports both, and `query.py`
   aggregates them:

```
cutoff_for(source, on) -> cutoff: calls
  2026-09-30 purchase -> 2025-10-01: 2476
  2026-10-01 purchase -> 2025-11-01: 1842        # the business date was 2026-09-30
  ...
expired points by earning month and source
  2025-09 purchase: 407230                       # = the audit's purchase figure
  2025-10 purchase: 244231                       # shouldn't have expired
  2026-06 promo: 59071                           # = the audit's promo figure
  2026-07 promo: 27722
```

The aggregation matches the audit's figures line by line. It shows that the cutoff date `on` changed during the run,
and `due_lots` is called without `on` (`named: {}`). Two queries and about 20 lines of Python.

## Clock simulation (`sim/sitecustomize.py`, not visible to the agent)

record.sh, validate.sh and the oracle put `sim/` on `PYTHONPATH`, and it chains the system's own `sitecustomize`.
- **Start.** The clock starts at `SIM_START`.
- **Advancing.** It moves forward by `SIM_STEP` seconds only on clock reads made from code under `SIM_ROOT` (the
  job). Reads by `logging`, the recorder or the standard library see the time without moving it, so recording
  doesn't shift midnight.
- **Sleep.** `time.sleep` advances the clock instead of sleeping.
- **What it patches:**
  - `time.time/time_ns/monotonic/localtime/gmtime/ctime/strftime`;
  - `datetime.datetime.now/today/utcnow` and `datetime.date.today`. Checked: replacing `clock.now()` with
    `datetime.now(ZONE)` still sees the simulated clock, and the oracle grades the same.
- **The CRM.** `urllib.request.urlopen` answers requests to the CRM host with 202, so the trace shows the
  production endpoint.

The timing is set by the job's own clock reads: about 3.6 per member at month end, about 3 per activity record. The
production story is "the CRM was slow that night". Fair-play notes:
- **Fixes the oracle could misgrade.** A fix that reads the clock through an API the simulation doesn't patch would
  see the real clock: `os.times`, a subprocess `date`, or C extensions. A correct fix doesn't care about the clock
  after start, but a fix that *reads* the date in a new way at start would get the real date (October 2026) and
  fail. We consider this unlikely.
- **Timing changes with the fix.** A fix changes the number of clock reads, and so where midnight falls. Correct
  results don't depend on it.

## Oracle (`oracle.py <dir>`, about 30 s, five runs in parallel)

Each run uses a hidden database under a simulated start time. The JSON report (`posting`, `expiry`, `statements`,
`liability`) is compared with the truth computed independently by `gen/gen_db.py`.

| case | database | start, step | checks |
|---|---|---|---|
| h1-original | the private Sep 30 snapshot | 2026-09-30 23:50:02 CEST, 0.048 | the failing run |
| h1-late-start | same | 23:59:30, 0.048 | almost every member after midnight; same truth |
| h2-october-cet | seed 31026, 4,200 members | 2026-10-31 23:50:02 CET, 0.048 | 31-day month in CET, crossing into November |
| h3-quick-month-end | seed 8312, 3,600 members | 2026-08-31 23:50:02, 0.012 | month end finishing before midnight (regression) |
| h4-daily-crossing | seed 9292, 3,000 members | 2026-09-29 23:58:30, 0.048 | daily run crossing into the month's last day: no expiry and no statements (catches fixes that re-decide the mode per batch) |

**Results:**
- pristine: FAIL (h1, h1-late-start, h2);
- reference fix: PASS;
- `wrong-fix.patch` (cutoff one month earlier): FAIL (h1, h2, h3);
- reference fix with `clock.now()` using `datetime.now(ZONE)`: PASS.

## Recording (`record.sh`)

The private snapshot is copied to `mktemp/srv/loyalty/data/points.db`. `nightly.py --db … --out …` is recorded under
the simulated clock, with cwd=WORKDIR. Only `WORKDIR/report.pmdb` is written.

| measure | value |
|---|---|
| failing run | about 5 s real (16 min simulated) |
| recording | 19–40 s |
| trace | 76 MB (`du`: 82M), 336k observations |
| `pmdb show functions` | about 9 s (debug build) |
| `query.pmdb` (two selects + exports) | about 32 s (debug build) |

Shaped for the recorder:
- `dates.py`'s month arithmetic is `lru_cache`d;
- rows become NamedTuples inline;
- the liability groups lots by earning date in SQL;
- `points_expiring` compares earning months;
- expiry asks the policy once per member (`due_lots`), not once per lot. A per-lot first version gave 318 MB
  (3.1M observations).

These are ordinary optimisations, and don't hint at the bug.

## Fairness threats

- **The log shows the midnight crossing in plain sight.** A reader who checks timestamps against the 23:50 cron gets
  the key fact without the trace. That is intended: it keeps arm A viable.
- **The forecast is a hint.** The "expiring 2026-10-31" figure in the issue's table (342,633 vs 615,986) shows that
  next month's lots were consumed.
- **`due_lots`' docstring says "(default: today)"**, which is honest but greppable.
- **The issue says posting and the August month end were right.** That narrows the search to the September
  month-end stage. In this story, August's run finished before midnight (h3).
- **Every month end would cross midnight at this pace.** The run takes 16 simulated minutes from 23:50. The story is
  that the CRM was slow that night, but the code doesn't show the normal pace. An agent may wonder why August was
  fine.
- **The trace is large and query-heavy** (32 s per export pass on the debug build), which works against arm B.

## Validation (`validate.sh`)

1. **The failing run.** On the private snapshot under the simulated clock, it reproduces:
   - expired 742,058 points, outstanding 16,071,024, EUR 65,891.20;
   - the log and reports in `work/`, byte for byte after the path rewrite. They end at 00:06:13.
2. **Pristine work.** The oracle fails.
3. **The fixes.**
   - `fix.patch` applies, and the fixed run gives the audit's figures: 468,705 expired, 16,344,377 outstanding,
     EUR 67,011.95, 615,986 expiring 2026-10-31. The oracle passes.
   - `wrong-fix.patch` fails the oracle.
4. **Recording and query.** `record.sh` writes `report.pmdb` and changes nothing else. The output of `query.pmdb` +
   `query.py` contains `query_expect.txt`.

## Regeneration

```
python3 gen/gen_db.py --seed 20260930 --members 4800 --run-date 2026-09-30 --out private/points-2026-09-30T2350.db --truth private/expected-2026-09-30.json
cp private/points-2026-09-30T2350.db hidden/h1-original.db; cp private/expected-2026-09-30.json hidden/h1-original.truth.json
python3 gen/gen_db.py --seed 31026 --members 4200 --run-date 2026-10-31 --out hidden/h2-october-cet.db --truth hidden/h2-october-cet.truth.json
python3 gen/gen_db.py --seed 8312 --members 3600 --run-date 2026-08-31 --out hidden/h3-quick-month-end.db --truth hidden/h3-quick-month-end.truth.json
python3 gen/gen_db.py --seed 9292 --members 3000 --run-date 2026-09-29 --out hidden/h4-daily-crossing.db --truth hidden/h4-daily-crossing.truth.json
```

Delete a target `.db` before regenerating it: the generator's `CREATE TABLE` fails on an existing file.

`work/logs` and `work/reports` come from the failing run in a scratch tree laid out as `/srv/loyalty/{nightly,data}`,
with the scratch prefix removed (validate.sh step 1 does exactly this and compares).
