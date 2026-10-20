# refund-postmortem: notes

**Kind:** a post-mortem of a run that can't be replayed. A production job ran over private data. The agent gets the
code, the job's INFO log of that run, the report it wrote, and the issue with the expected numbers. It never gets the
input. Arm B also gets `report.pmdb`, a trace of that run.

## The program (`work/`, 816 lines of Python in 13 modules, plus config, log and report)

`monthly_report.py` reconciles a month of card-payment provider events (the webhook archive, JSONL.gz) into one book
per provider: gross, fees, refunds, disputes and net, in EUR. Three adapters (`recon/providers/kestrel.py`,
`lumen.py`, `novapay.py`) turn each provider's event format into a `Txn` NamedTuple. The other modules are the loader
(streaming read, redelivery de-duplication by event id, month window, sort), FX conversion for Lumen, money parsing,
checks, the ledger and the report.

## The bug

NovaPay accounts migrated to API 2026-08-01 (half of them, from 12 September) send a **refund lifecycle**: one
`refund` event when a refund is created (status `pending`, or `succeeded` for instant refunds), then another `refund`
event with the **same refund id** whenever its status changes. Shapes in the private data (seed 20260932):

| shape | count |
|---|---|
| old API, single `succeeded` event | 226 |
| pending → succeeded | 65 |
| instant succeeded | 25 |
| still pending at month end | 20 |
| pending → failed | 8 |
| pending → succeeded → succeeded (metadata update) | 7 |
| pending → succeeded → failed (reversal) | 3 |

`Ledger.apply` books every event whose status isn't `failed`/`canceled` as a new refund:
- pending → succeeded is counted twice;
- pending → failed is counted once (the pending event);
- refunds still pending are counted;
- metadata updates are counted again;
- reversals are counted twice.

NovaPay's refunds come out at 16,966.45 instead of 11,938.78 (+42%), and net at 326,640.25 instead of 331,667.92.
Kestrel and Lumen are exact.

**Fix** (`fix.patch`, `recon/ledger.py` only): keep the latest `Txn` per refund id, and count a refund in `refunds`
only if its last status is `succeeded`. Refunds bypass the status filter so that a later `failed` can replace an
earlier status.

**Why the faulty code looks right.** Nothing in the code is wrong for the event formats the code knows: one event per
refund. The status filter (`ignored_statuses = failed, canceled` in `settings.toml`) is reasonable for one-event
refunds and failed charges. The loader visibly de-duplicates redelivered events (by event id, and the log says
"dropped 43 redelivered events"), which tells a reader that duplicates are handled. The NovaPay docstring mentions API
2026-08-01, but only for the amount format, which the adapter does handle. The defect is in how the data behaves, and
only the private input shows it.

## Why reading alone is hard

The issue points at NovaPay's refunds, so a reader reaches `novapay.py` and `Ledger.apply_refund` quickly. Every line
there is plausible. +42% isn't a factor that suggests units (×100) or a sign error. Plausible hypotheses a reader can't
test without the data:
- FX on refunds (but NovaPay is all EUR);
- refunds of charges from earlier months (the log shows 35);
- partial refunds;
- fees on refunds;
- events at the month boundary;
- duplicates (but the loader de-duplicates);
- counting pending refunds;
- a lifecycle of several events per refund.

**What a strong reader would likely try first.** "Pending refunds shouldn't count yet": add `pending` to
`ignored_statuses`. That gets close but is still wrong, because the metadata updates and reversals remain. Its
oracle result is FAIL on h1/h2/h3, e.g. h1 refunds 12,307.49 instead of 11,938.78. Being close can tempt the agent to
stop. Neither arm can check against the private data.

**How a strong reader could still find it.** If the model knows Stripe-like APIs (`refund.created` and
`refund.updated` events), it may guess a lifecycle and write the defensive fix (latest event per refund id, count only
`succeeded`) without evidence. That fix is the reference one. Count it as a risk to the scenario's discrimination: a
lucky or knowledgeable arm A can pass.

## Arm A (without pmdb): likely course

There is no input to replay. The agent can only:
- read the code and the log, and form hypotheses;
- write synthetic exports to test them. Each test checks only the shape it invents, not what NovaPay sent.

It can't measure which hypothesis explains the €5,027.67, so it either guesses one fix (pending, de-duplication) or
writes a broad defensive one. Prints and pdb are useless without the input.

## Arm B (with the trace): how pmdb shortens it

The trace has every `Txn` the ledger booked (`Ledger.apply(self, t) -> booked`, `Ledger.apply_refund(self, book, t)`),
and every raw event (`normalize(raw, fx)`, with `raw.body`). `query.pmdb`:

```
select /Ledger\.apply_refund/(_, _, t) where t.status != "succeeded"
select /Ledger\.apply/(_, t) -> booked where t.ref == "npr_h63pf8nscp87we"
show $1
```

Output (abridged):

```
$0 = <103 element(s) in 1 trace(s)>        # 103 refunds booked while pending
$1 = <3 element(s) in 1 trace(s)>
.../ledger.py: call Ledger.apply(<...Ledger object...>, {... kind: refund, ... ref: npr_h63pf8nscp87we, settle_amount: 2864, status: pending, ts: 1789806247}) -> true
.../ledger.py: call Ledger.apply(<...>, {... ref: npr_h63pf8nscp87we, settle_amount: 2864, status: succeeded, ts: 1789857106}) -> true
.../ledger.py: call Ledger.apply(<...>, {... ref: npr_h63pf8nscp87we, settle_amount: 2864, status: failed, ts: 1789879482}) -> false
```

The second query uses a ref taken from the first one's output. It shows one refund booked twice (pending, succeeded)
and then reversed, which reveals both the lifecycle and the "final status wins" rule.

A natural route without knowing the bug:
1. `select /Ledger\.apply_refund/(_, _, t) where t.provider == "novapay"`, then `show`, to see the refunds.
2. Statuses `pending` appear, and repeated `ref`s.
3. Query a ref to see its events.
4. `select /Ledger\.apply/(_, t) -> booked where t.kind == "refund" && t.status == "failed"` finds the 11 failed
   updates, 3 of which follow a `succeeded`.

The agent can even check the fix against the statement before writing it: `pmdb --export-xml` + Python can recompute
the NovaPay refunds by final status from the trace. That gives 11,938.78 exactly.

## Oracle

`oracle.py <dir>` runs the agent's job on four hidden exports (`hidden/`). It compares the per-provider totals in its
JSON report with the providers' statements, computed independently by the generator (`*.truth.json`).

| dataset | content |
|---|---|
| h1-original | the private failing export |
| h2-all-migrated | every NovaPay account on the new API from 3 Sept; 31 reversals, 27 metadata updates, 35% multi-part refunds of one charge (catches de-duplication by charge) |
| h3-processing | 27 lifecycles with an extra `processing` status (catches "ignore pending" fixes that count other intermediate statuses) |
| h4-legacy-only | no migrated account (regression: the old behaviour must be kept) |

The oracle is deterministic and takes about 1.5 s. Checked:
- pristine work: FAIL (h1, h2, h3);
- reference fix: PASS;
- "add pending to ignored_statuses": FAIL (h1, h2, h3).

h3's `processing` status doesn't appear in the private data. A fix that keys refunds by id with the last status
winning handles it anyway; a fix that enumerates statuses may not. h3 is the one hidden check beyond what the trace
shows.

## Recording (`record.sh`)

`record.sh [WORKDIR]` copies the private export to a `mktemp` directory under `exports/`, so the trace shows that path
and not the scenario's. It then records `monthly_report.py --export … --month 2026-09 --out <tmp>`, with cwd=WORKDIR.
It writes only `WORKDIR/report.pmdb`.

| measure | value |
|---|---|
| failing run | 0.8 s |
| recording | 14–24 s on a loaded machine |
| trace | 48 MB, 317k observations, 45 functions |
| `pmdb show functions` (load) | about 7 s |
| a regex query over `Ledger.apply` | 20–40 s at load average 16 on 14 cores (expect about half unloaded) |

Building the trace exposed a recorder problem worth logging: **the recorder pickles `self` and every other object
argument on every call.** A ledger whose state grows (a map of all charges) made the first trace **11 GB** (7 minutes),
and an FX table with 125 rates added about 100 bytes × 12k calls. To keep the trace small, the code was shaped in
ways that are realistic but were chosen for recording:
- the FX table caches lookups with `functools.lru_cache`, and each book numbers its entries with `itertools.count`.
  Both are unpicklable, so the recorder stores a short repr;
- the loader is a generator pipeline, so whole-export lists aren't recorded as arguments;
- per-transaction counting is inlined in the booking loop.

Fairness:
- these choices don't hint at the bug;
- they make `self` opaque in the trace, as the skill says objects are;
- the per-transaction `Txn` and raw event bodies stay fully queryable.

## Threats to fairness

- **Domain knowledge.** Stripe-like webhook lifecycles are well known, and a model may guess them; see above.
- **The log.** NovaPay's refund ratio (421 refund events / 6,233 charges = 6.8%) is higher than Kestrel's (5.6%) and
  Lumen's (4.4%). A reader who computes this gets a weak hint of extra refund events.
- **The issue names the provider and the column** (refunds), as a real finance report would. That narrows reading to
  about 100 lines but doesn't reveal the mechanism.
- **"August reconciled fine"** hints at a change in September, realistically. Combined with the API-version
  docstring, it can lead a reader to the migration.
- **Arm B's trace is large and queries are slow** (tens of seconds). A query error or a broad `show` costs time,
  which works against pmdb, not for it.
- **The trace contains the private data.** That is the premise: post-mortem traces are recorded in production.

## Validation (`validate.sh`, all PASS, 39 s)

1. The failing run on the private export shows NovaPay refunds 16,966.45 and net 326,640.25, identical to
   `work/reports/payout-recon-2026-09.txt`.
2. The oracle fails on pristine work.
3. `fix.patch` applies. The fixed run shows refunds 11,938.78, net 331,667.92 and total net 1,028,584.40, and the
   oracle passes.
4. `record.sh` writes a 49 MB `report.pmdb` and leaves every other file unchanged. The output of `query.pmdb`
   contains every line of `query_expect.txt`.

## Regenerating the data (`gen/gen_events.py`)

```
python3 gen/gen_events.py --seed 20260932 --p-reversal 0.03 --out private/events-2026-09.jsonl.gz --fx-out work/config/fx/2026-09.csv
python3 gen/gen_events.py --seed 7101 --migrated 1.0 --migration-day 3 --p-reversal 0.06 --p-meta-update 0.08 --partial-burst 0.35 --np-refund-rate 0.06 --out hidden/h2-all-migrated.jsonl.gz
python3 gen/gen_events.py --seed 7102 --migrated 0.67 --p-extra-processing 0.3 --p-reversal 0.04 --out hidden/h3-processing.jsonl.gz
python3 gen/gen_events.py --seed 7103 --migrated 0.0 --out hidden/h4-legacy-only.jsonl.gz
```

`private/statement-truth.json` is h1's truth (`hidden/h1-original.jsonl.gz` is a copy of the private export). The
log and report in `work/` came from a run in a scratch tree under `/srv/...`. Their timestamps were shifted to
2026-10-01 03:10 and their paths stripped to `/srv/...`. `work/README.md` is the job's operations note.
