# payroll-postmortem: notes

**Kind:** a post-mortem of a run that can't be replayed, because the input was private and deleted. The September
payroll ran on HR's export, which holds personal data (names, IBANs, birth dates, tax classes) and was deleted
after the bank acknowledged the transfers. The agent gets the code, the INFO log of that run, the register it
wrote, and the issue with HR's figures. It never gets the export. Arm B also gets `report.pmdb`, a trace of that
run.

## The program (`work/`, 1,103 lines of Python in 18 modules, plus config, log and register)

`run_payroll.py` pays ~650 persons (619 employed in September; 393 salaried, 226 hourly) of a logistics company
in seven cost centres.
- **Input.** `hrexport.py` reads the export: persons with assignment rows, absences and timesheets.
  - Assignment rows hold the contract terms in force between `valid_from` and `valid_to`.
  - The schema is in its docstring.
- **Salaried pay.** `salaried.py` prorates the monthly salary by calendar days of employment.
- **Hourly pay.** `hourly.py` pays from the timesheets: night, Sunday/holiday and weekly overtime premiums, and
  paid absences at contract hours.
- **Allowances.** `allowances.py` pays a meal allowance per employed weekday without an absence.
- **Contributions.** `contributions.py` applies ceilings prorated by employed days.
- **Tax.** `tax.py` is a banded simplified tariff.
- **Other modules.**
  - `employment.py`: employment span and the row in force on a day.
  - `absences.py`, `validation.py` (IBAN mod-97 and master-data checks), `checks.py`, `register.py`, `report.py`
    and `bankfile.py`.
  - `periods.py`, `money.py` (integer cents, round half up), `settings.py` (TOML).

## The bug

`employment.employment_for` builds a person's employment as
`(first row's valid_from, last row's valid_to)`, with the rows as segments. Its docstring states HR's convention:
every change closes a row and opens the next, so rows follow each other. It checks that rows don't **overlap**.
`employed_days` takes the period's days inside that span. `segment_at` returns the row in force on a day by
bisecting on the rows' starts, without looking at the row's end.

When a person has a **gap** between two rows, the gap days count as employed, and `segment_at` returns the
earlier row. So:
- salaried staff are paid that row's salary for the gap;
- everyone gets the meal allowance on gap weekdays;
- contribution ceilings are prorated over too many days.

Gaps happen when:
- a fixed-term contract ends mid-month and the follow-on contract, already entered, starts on Oct 1;
- seasonal staff leave and are re-hired;
- a contract ended in August and a new one starts mid-September.

In the private export (seed 20260930), 9 of 650 persons have a gap in September (8 salaried, 1 hourly):

| shape | persons | example |
|---|---|---|
| ends mid-September, follow-on from Oct 1 | 4 | P10085: row to 09-20, next row from 10-01 → paid 10 extra days |
| leaves and is re-hired within September | 3 | P10719: to 09-09, again from 09-19 (another cost centre) |
| ended in August, new row from mid-September | 2 | P11724: to 08-27, again from 09-08 → paid 09-01..09-07 |

Every other multi-row person is right:
- 44 contiguous changes in September (rate rises, cost-centre moves);
- 14 old gaps before 2026, which don't touch the period.

Joiners, leavers, persons who left earlier and future hires are right too. Base salaries come out €16,904.43
too high, and allowances €502.50 too high (67 days × €7.50). Contributions, tax and net follow; hourly pay,
premiums and headcount are exact.

**Fix** (`fix.patch`, `payroll/employment.py` only): `employed_days` keeps only the days that one of the rows
covers. Equivalent fixes pass too, such as building one span per run of contiguous rows, or making `segment_at`
return None past a row's end with the callers skipping such days.

**Why the faulty code looks right.**
- The span is exactly right for the convention the docstring states, which holds for 98.6% of persons, and for
  every contiguous change.
- The overlap check shows the author thought about how rows relate.
- `segment_at` is the textbook bisect lookup for back-to-back intervals.
- Nothing about gaps appears anywhere, and the defect only shows on data the agent can't see.

## Why code and log alone don't suffice

The log gives counts (650 persons, 903 rows, 619 payslips, 31 part-month), and the register gives totals per cost
centre. None of these shows which persons were overpaid. The issue says base salaries and allowances are too high
in five of seven cost centres, with hourly pay and headcount exact. Plausible hypotheses that a reader can't test
without the data:
- unpaid leave not deducted, which would also raise allowances;
- the absence precedence;
- proration of joiners and leavers (`first`/`last` clipping);
- the 30-day convention in `contributions` against calendar days in `salaried`;
- holidays counted for allowances (September has none);
- rounding;
- a rate change applied on the wrong day (contiguous changes);
- `parse_amount` with one-digit decimals;
- rows exported in random order, which the code sorts.

## What a strong reader would try first, and arm A's route

1. **Arithmetic on the issue.** Both differences can come from days counted as employed: allowances +502.50 is
   exactly 67 × 7.50, so there are extra weekdays. Unpaid leave is the first suspect. Reading `absences.py` and
   `salaried.py` shows they are consistent, so the extra days must come from `employed_days`.
2. **Reading `employed_days`.** It clips the span to the period correctly. The question becomes "when is the span
   wrong?". The docstring's "rows follow each other" invites "what if they don't?". The overlap check next to it,
   with no gap check, is the tell.
3. **Confirming with a synthetic export.** The schema is documented, so the agent can write a two-person export
   with a gap and run the job (0.2 s) to see the gap paid. Then it writes the fix.

We expect a strong reader to need roughly 10–25 turns: the symptom points at days, but several day-counting
hypotheses must be eliminated by reading first. Arm A is not hopeless. The issue's two differences and the
module docstrings are enough to get there, but the agent can never confirm that gaps explain *all*
€16,904.43, only that they could.

## Arm B (with the trace): how pmdb shortens it

The trace holds every person's rows (`employment_for(id, rows) -> employment`) and every day lookup
(`segment_at(segments, day) -> row`, 23k calls) with the call site. `query.pmdb` + `query.py`:

```
select segment_at(segments, day) -> s where s.valid_to != none
export $0 to "lookups.jsonl"
select employment_for("P10085", rows) -> e
show $1
```

`query.py` keeps the lookups whose day is after the returned row's `valid_to`, and sums the salary of those coming
from `salaried.py`:

```
9 persons paid on days after their assignment row ended
P10085: 10 days 2026-09-21..2026-09-30 on row A20195 (ended 2026-09-20, next row from 2026-10-01, salaried)
...
P11526: 8 days 2026-09-01..2026-09-08 on row A23226 (ended 2026-08-27, next row from 2026-09-09, hourly)
salary paid for those days: 16,904.43
```

The sum matches the issue's difference to the cent, so the agent can check its explanation before fixing.

A natural route without knowing the bug:
1. `show functions`.
2. `select base_salary(e, days, unpaid, n) -> b`, then `export` and recompute each person's salary from their rows
   and days in Python. The 9 persons whose `days` run outside their rows stand out, as does
   `employment_for(...) -> {end: none, ...}` for a person whose first row ends mid-September.
3. Or start from the allowances: `meal_allowance(days, absent, 750) -> a` and compare `days` with the rows.

## Oracle

`oracle.py <dir>` runs the agent's job on four hidden exports. It compares every per-cost-centre and total column
of the JSON register, including headcount, with HR's calculation, which the generator computes independently
(its own day-by-day "is a row in force" logic, with Fractions; it doesn't import the job). Truth equals the fixed
job's output to the cent on all four sets, and hourly pay and premiums equal even the pristine job's.

| dataset | content |
|---|---|
| h1-original | the private failing export (9 gaps) |
| h2-many-gaps | 43 gaps: follow-on, rehire, start, three-row inner gaps, gaps at the month's head and tail, and 3 persons with no row in September but rows before and after it (the bug pays them a full month and counts them in the headcount); 60% move cost centre |
| h3-hourly-gaps | 20 gaps, 90% of them hourly staff (only allowances and ceilings differ) |
| h4-contiguous | no gap in September (regression) |

The oracle is deterministic and takes 0.5 s.

| work | result |
|---|---|
| pristine | FAIL (h1, h2, h3) |
| `fix.patch` | PASS |
| `wrong-fix.patch` (skip days past the row's end in `base_salary` only) | FAIL (allowances, contributions, h2 headcount) |

## Recording (`record.sh`)

`record.sh [WORKDIR]` copies the private export to `<tmp>/srv/payroll/in/hr-2026-09.json` and records
`run_payroll.py --hr-export … --period 2026-09 --out <tmp> --bank-out <tmp>`, with cwd=WORKDIR. It writes only
`WORKDIR/report.pmdb`.

| measure | value |
|---|---|
| failing run | 0.2 s |
| recording | 4.3 s |
| trace | 42 MB, 299,973 observations, 58 functions |
| `pmdb show functions` (load, debug build) | 7 s |
| `query.pmdb` | 6 s |

All domain records are NamedTuples with ISO-date strings and integer cents. Each person's rows are passed per
call, so the trace stays small. `Register` (`self`) is opaque.

## Threats to fairness

- **The allowance difference is a strong clue.** +502.50 = 67 × €7.50 points at extra employed weekdays. That is
  intended: it is arm A's route. A reader who doesn't do the division loses it.
- **The docstring states the convention** that gaps break, and the overlap check is next to it. A reader who
  questions conventions finds the bug by reading.
- **Domain knowledge.** Rehires and fixed-term follow-ons are well-known payroll edge cases.
- **The per-cost-centre table** shows two office cost centres unaffected, as a real comparison would. That narrows
  little.
- **The log** reports "31 for part of the month". With the fix it would be 40. HR's count isn't given, so it is
  not a lead.
- **The trace contains the personal data.** That is the premise of a production post-mortem trace.
- **Arm B's natural first query may be broad** (`base_salary` with 30-element day lists, 619 calls). It is fine
  through `export`, but noisy through `show`.

## Validation (`validate.sh`, all 12 steps PASS, 14 s)

1. The failing run on the private export writes the register in `work/reports` (identical but for the Generated
   line) and the log in `work/logs` (identical but for timestamps and paths). Its totals are base 2,163,813.44,
   allowances 94,747.50 and net 2,015,999.07.
2. The oracle fails on pristine work.
3. `fix.patch` applies. The fixed run gives HR's preview (base 2,146,909.01, net 2,005,844.58), and the oracle
   passes. `wrong-fix.patch` fails the oracle.
4. `record.sh` writes `report.pmdb` and nothing else. The output of `query.pmdb` + `query.py` contains every line
   of `query_expect.txt`.

## Regenerating the data (`gen/gen_hr.py`)

```
python3 gen/gen_hr.py --seed 20260930 --out private/hr-2026-09.json --truth-out private/hr-2026-09.truth.json
cp private/hr-2026-09.json hidden/h1-original.json; cp private/hr-2026-09.truth.json hidden/h1-original.truth.json
python3 gen/gen_hr.py --seed 7201 --gaps follow:10,rehire:8,start:6,through:3,inner:4,head:4,tail:4 --gap-new-cc 0.6 --gap-hourly 0.3 --out hidden/h2-many-gaps.json --truth-out hidden/h2-many-gaps.truth.json
python3 gen/gen_hr.py --seed 7202 --gaps follow:6,rehire:8,inner:3,head:3 --gap-hourly 0.9 --out hidden/h3-hourly-gaps.json --truth-out hidden/h3-hourly-gaps.truth.json
python3 gen/gen_hr.py --seed 7203 --gaps "" --out hidden/h4-contiguous.json --truth-out hidden/h4-contiguous.truth.json
```

The log and register in `work/` came from a run in a scratch tree laid out as `/srv/payroll/{app,in,out}`.
Their timestamps were shifted to 2026-09-30 22:30:02, and the scratch prefix was stripped.
