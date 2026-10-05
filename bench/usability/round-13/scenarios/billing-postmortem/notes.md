# billing-needle (scenario 1: needle in a haystack)

## The program and the symptom

`work/` is a monthly electricity billing run (898 lines: `run_billing.py` and the package
`billing/`: accounts, feeds, meters, estimate, tariffs, bills, cycle, validation, report). It
reads a register of 3,100 customer accounts, five tariffs, meter-exchange events and 6,428
readings from three meter operators with different formats (Telemetrix: semicolon CSV, decimal
commas, dials; GridSense: CSV with CT ratios; Meterline: JSONL in Wh). It writes a bill per
account, an exceptions report and a summary.

The user's MDM total of validated consumption is 1,941,139.9 kWh. The run reports
1,941,062.2 kWh, so it is 77.7 kWh short. The bill count (3,070) and the estimated bills (104)
are right, and no bill is in the exceptions report.

## The bug

`feeds.load_all` merges the operators' streams in `reading_order` = (raw account id as
delivered, meter, time). `cycle.account_batches` then groups that stream into per-account
batches. It resolves each raw id (current *or* legacy Northwind number) to the register's id,
and flushes a batch whenever the resolved id changes. `run_cycle` stores
`issued[account_id] = settle_account(...)`.

Exactly one account is affected: AC-252187, legacy NW-43185. Its Telemetrix meter was exchanged
on 17 September for a Meterline smart meter. Telemetrix reports the account under the legacy
number, while Meterline always uses current ids. In the merged stream, its readings therefore sit
under "AC-252187" (new meter) and, much later, under "NW-43185" (old meter). The account is
settled twice, and the second bill (old meter, 110.1 kWh) overwrites the first (new meter,
77.671 kWh). The missing 77.7 kWh is the new meter's consumption.

The fix (`fix.patch`, in `cycle.account_batches`) collects all batches before yielding them,
and sorts each by (meter, time).

**Why the code looks plausible.** Each piece is reasonable on its own:
- Merging pre-sorted streams by account is standard.
- Streaming per-account batches assumes a sorted stream, which the merge appears to provide.
- Resolving legacy ids is documented.
- `issued[...] = ...` is the natural way to collect bills.

The defect lies between two modules: the sort key is the raw id, the grouping key the resolved
one. These differ only for an account reported under two different ids. Only one record in this
data does that, a property of the data that no code shows.

## Why reading alone is hard (and what a reader would suspect first)

- The symptom names no feature: a 77.7 kWh shortfall in an aggregate of ~1.94 GWh over ~3,000
  bills. It is not a round number, and it has no other tell.
- The natural suspects are:
  - rounding in `meters`/`bills` (77.7 kWh is too much for rounding over 3,000 accounts, but a
    reader has to work that out);
  - rollover handling in `register_advance`;
  - meters skipped as implausible, or with a single reading (`account_consumption`);
  - the duplicate filter in `feeds._deduplicate`;
  - the in-window filter (`periods.in_window`);
  - proration;
  - estimation (excluded by the issue, which a reader may not trust).

  Each of these is correct.
- Finding the bug by reading requires two steps:
  1. noticing that `account_batches` relies on the stream being sorted by the *resolved* id;
  2. tracing the merge key back to `feeds.reading_order`, and realising that legacy ids make
     raw and resolved ids differ.

  Even then, the reader can't confirm that any account is actually reported under two ids
  without searching the data.
- **Honest risk.** A strong reader who reads `cycle.py` (70 lines) with the question "how can
  consumption disappear without losing a bill?" may spot the `issued[...]` overwrite plus the
  flush-on-change grouping within ~10 turns. The `Register` docstring mentions that "some meter
  operators still report under [the legacy number]", which is a fair, realistic clue. I estimate
  that reading alone takes Opus 10–20 turns, but it is not hopeless.

## How an agent without pmdb would proceed

The data is available and the run takes ~1 s, so prints are cheap. The likely routes:
- **Reconcile per account.** Write a script that recomputes each account's consumption from the
  raw feeds (reusing `billing.feeds`/`billing.meters`) and diffs it with `bills_2026-09.csv`.
  - The agent has to group the readings itself. If it groups them by resolved id, it finds
    AC-252187 (187.771 vs 110.1).
  - If it groups them by raw id, as the feeds deliver them, the two halves show up as two
    "accounts", and the legacy one isn't in the bills.
  - Roughly 4–8 turns of scripting and debugging the script.
- **Print or log in `account_batches`/`run_cycle`** to detect an account settled twice. This
  needs the hypothesis first.
- **Audit the meter exchanges.** `meter_events.csv` lists 6. Checking each exchanged account's
  bill against its feed readings finds it, but `grep AC-252187` finds no Telemetrix reading,
  because they are filed under NW-43185.

## How pmdb shortens it

The trace has every `account_consumption` call with its readings and its result. The user's
discrepancy turns into a single query:

```
select account_consumption(k, rs, _) -> c where c != none && c > 77.65 && c < 77.75
show $0
```

This gives 2 matches: AC-115591 (a rolled-over meter, 77.7 kWh, a coincidence) and AC-252187,
whose readings come from an `install` reading of meter ML-D5F26F, with the exchanges argument
non-empty. Following up on that account:

```
select account_consumption("AC-252187", rs, _) -> c
show $1
```

```
$1 = <2 element(s) in 1 trace(s)>
.../billing/cycle.py:43: call account_consumption(AC-252187, [{account: AC-252187, ..., kind: install, meter: ML-D5F26F, ...}, ...], [...]) -> 77.671
.../billing/cycle.py:43: call account_consumption(AC-252187, [{account: NW-43185, ..., meter: TX7278945, ...}, {..., kind: removal, ...}], [...]) -> 110.1
```

The account is settled twice, once per spelling of its id. Together with
`issued[account_id] = ...`, this points straight at the grouping in `cycle.account_batches`.
An agent that doesn't think of matching the discrepancy can find the same thing with
`select account_consumption(k, rs, ex) where ex.len() > 0` (6 exchanged accounts expected,
7 calls, one account twice). That still requires counting by eye.

## Threats to fairness

- **Arm A has every input.** A disciplined per-account reconciliation finds the account without
  pmdb. The advantage is in turns (no reconciliation script to write and debug), not in
  feasibility.
- **The discrepancy query is a technique an agent must think of.** Its first answer contains a
  coincidental match.
- **The trace is large and queries are slow.** It is 60 MB, with ~130k calls: `Register`
  methods record the pickled register, and `run_cycle`, `write_bills` and `summarize` record
  all the readings and bills. Each pmdb invocation takes 7–14 s to load it.
- **The oracle requires a complete fix.** It checks bills on the original data plus two fresh
  datasets: a GridSense legacy meter exchanged for Meterline (h1), and a Telemetrix legacy and a
  non-legacy GridSense "AC123456" vs Meterline "AC-123456" exchange (h2). A data patch or a
  hard-coded account fails.
  - A strict case (h3, `--strict` only) has one legacy account whose closing read arrives under
    its current id. Its two reads then arrive out of time order.
  - A fix that merely concatenates an account's batches passes the required cases but not h3. A
    fix that sorts by resolved id, or collects and sorts per account, passes all of them. Both
    were checked.

## Recording

- `record.sh` records `python3 run_billing.py --period 2026-09 --data data --out <tmp>` in
  WORKDIR.
- **Recording takes 8–19 s** (19 s with the other scenarios' builds running in parallel); the
  plain run takes 0.8 s.
- **The trace is 60 MB:** ~130k calls, of which 3,071 are `account_consumption`.
- **pmdb takes 7–14 s per invocation** to load the trace.
- **Finding during the build:** the first version called `Register.resolve` per reading. Since
  `self` is opaque, the recorder pickled the whole register (3,100 accounts) on each of ~10k
  calls. Recording didn't finish within 2 minutes and used 2.4 GB. The program now looks ids up
  in a dict. This is a real pmdb-record hazard for programs with methods on large objects.
- **Finding:** a pmdb script line holding only a `# comment` fails with "expected command",
  although the README says comments run to the end of the line. Trailing comments work.

## Validation (`validate.sh`, all PASS)

1. The failing run on pristine work prints `metered consumption 1,941,062.2 kWh` and 3,070 bills
   (MDM: 1,941,139.9).
2. The oracle fails pristine work: original, h1 and h2 each differ on the exchanged accounts.
3. With `fix.patch`:
   - the run prints 1,941,139.9 kWh;
   - the oracle passes, including `--strict`.
4. `record.sh` on a temp copy:
   - writes `report.pmdb` and nothing else (`diff -r`: only report.pmdb);
   - `query.pmdb`'s output contains every line of `query_expect.txt`.

## Files

- `gen/make_data.py` generates the data and names the needles.
- `gen/make_hidden.sh` regenerates `hidden/`: datasets plus the expected outputs of the fixed
  program.
- `gen/truth_original.json` holds the MDM total and the needle of the work data.
