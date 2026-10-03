# card-ledger-queue: notes

**Kind:** a post-mortem of a run that can't be replayed because its input was a queue that is now empty. The job
drained a day's card-processor notifications from a standard (at-least-once, unordered) queue and deleted them as it
posted them. The agent gets the code, the job's INFO log, the settlement summary it wrote, and the issue with the
bank's figures. Arm B also gets `report.pmdb`, a trace of that run.

## The program (`work/`, 1,084 lines of Python in 16 files, plus config, log and summary)

`run_ledger.py` is the daily ledger run of a prepaid-card programme. It drains the `card-events-prod` queue in
batches of 10 (`ledger/queue_client.py`: the production gateway client, or a queue dump with `--spool`, documented in
the README), parses each message (`messages.py`), drops repeats (`dedup.py`), and applies each new notification
(`consumer.py`):
- authorizations open holds (`holds.py`);
- reversals release them;
- clearings consume holds (partial and final presentments, over-presentment) and are posted with FX and ATM fees
  (`fees.py`);
- clearings or reversals that arrive before their authorization are parked and handled when it arrives
  (`parking.py`); what is still parked at the end is a late presentment, posted without a hold;
- refunds and top-ups are credited.

Postings are summed per card and per kind/merchant group (`postings.py`), checked (`checks.py`) and written as the
bank's end-of-day balance file and the settlement summary (`report.py`).

## The bug

`dedup.classify` recognises two kinds of repeats:
- queue redeliveries, by `MessageId` (correct);
- processor re-sends, which carry a new `event_id` (the processor's ids identify a delivery attempt). They are
  recognised by a fingerprint of the transaction: type, merchant id, card, amount, currency, `transaction_time`
  and `auth_code`.

Online transactions never collide on that fingerprint, because they have an authorization code and a timestamp to
the second. **Offline clearings** have neither: transit fares (MCC 4111), tolls (4784) and parking (7523), presented
by the operator the next day with `transaction_time` as a date and no `auth_code`. A rider who took two €2.90 trips
on the 27th produces two clearings that differ only in `network_ref`, the scheme's reference of the presentment. The
second one is dropped as a "processor re-send".

In the consumed queue (seed 20260928), 280 legitimate offline clearings on 202 cards were dropped:
- 255 transit, 24 tolls, 1 parking;
- €808.30 in all, which is exactly the difference with the bank.

The log's "421 processor re-sends" really are 141 re-sends plus these 280 fares. Everything else is right: holds,
parking, fees and late presentments.

**Fix** (`fix.patch`, one line in `ledger/dedup.py`): add `network_ref` to `IDENTITY_FIELDS`. Re-sends copy it, so
they are still recognised, while distinct presentments differ. Authorizations, reversals and top-ups have no
`network_ref` (`None`), so nothing changes for them. Equivalent fixes pass, e.g. deduplicating clearings and refunds
by `network_ref` alone.

**Why the faulty code looks right.**
- The dedup module's docstring explains, correctly, why the event id can't be used: it changes per delivery attempt.
- A fingerprint of "the fields that identify a card transaction" is what card people would write.
- `network_ref` reads like a technical id, of the same kind as the excluded `event_id`.
- The data model documents both `transaction_time` and the absence of `auth_code` for offline transactions, but in
  `messages.py`, not next to the fingerprint.
- Nothing in the code is wrong for online card traffic, which is 90 % of the volume.

## Why code and log alone don't suffice

The issue gives a total (€808.30 of clearings missing, on 202 cards, all debits). The log's counters don't reveal
it: nobody knows how many re-sends are normal. Plausible hypotheses that only the messages could test:
- out-of-order clearings parked and never posted (the parking module is the obvious suspect for a queue that
  doesn't keep order);
- late presentments;
- partial/split clearings consuming holds;
- over-presentment;
- the programme filter (37 notifications of another programme were skipped);
- unreadable messages;
- the batch acknowledgment (a crash between batches);
- redelivered messages with a new receipt handle;
- FX fees;
- the `check_balanced` invariant.

Each is correct. The amount (€808.30, ~€4 per card) is not a round number, a percentage or a single transaction.

**What a strong reader would likely try first.** The parking path: `finish()` posts leftover clearings and drops
leftover reversals, and a reader may suspect parked clearings are lost or posted twice. They aren't. Next comes
dedup, where the question is whether two *legitimate* events can share the fingerprint. Answering it needs knowledge
of offline card transactions (date-only transaction time, no auth code). The `messages.py` docstring states both,
so the clue is in the repo.

## Arm A (without the trace): a viable route

1. Read the issue: missing debits, all clearings, on many cards, a small amount each (~€4 per card). Small
   amounts on many cards suggest small frequent transactions.
2. Read the consumer. The places where a clearing can fail to post are `dedup.classify` (dropped as a repeat) and
   parking (posted at `finish`). A careful reading shows parking always posts.
3. Ask when two different clearings get the same fingerprint, then read the field documentation in `messages.py`:
   offline clearings have no `auth_code`, and their time may be a date.
4. Confirm with a self-made dump: two identical offline fares on one card → one posted. `--spool` and the README's
   message format make this a 20-line script.
5. Fix by adding `network_ref`, then check re-sends are still dropped.

We estimate 15–30 turns for a strong agent. The risk for arm A is stopping at a wrong but plausible fix (parking,
late presentments) that it can't check against the bank's numbers. The other risk is a fix that skips the
fingerprint for offline clearings, which double-posts offline re-sends. `wrong-fix-offline.patch` posts €32.20 too
much in h1 and fails all four oracle datasets.

## Arm B (with the trace): how pmdb shortens it

The trace has every `classify(message) -> verdict`, with the full message (a `Message` NamedTuple with the `data`
dict), every `on_clearing`/`post_clearing`, and every posting. A natural route from the issue: `show functions`
shows `classify` is called 9,455 times, as often as messages were received. Clearings are missing, so look at the
clearings that `classify` rejected.

```
select classify(m) -> "resend" where m.event_type == "clearing"
select classify(m) -> "new" where m.event_type == "clearing"
export $0 to "dropped.jsonl"
export $1 to "posted.jsonl"
select classify(m) -> "resend" from $0 where !m.data.has("auth_code")
```

`query.py` (20 lines) then compares the dropped clearings' `network_ref`s with the posted ones:

```
dropped clearings: 343; repeating a posted network_ref: 59; network_refs never posted: 280, total 808.30
never posted, by MCC: {'4111': 255, '4784': 24, '7523': 1}
never posted, with an auth_code: 0
posted  KP57382147 Rhein-Main Verkehrsverbund 3.40 2026-09-27 network_ref 77498836682347445772829
dropped KP57382147 Rhein-Main Verkehrsverbund 3.40 2026-09-27 network_ref 72394107667895564467293
```

The total matches the issue to the cent, and the pair shows the cause: the same card, fare and date, with
different presentments. Without `export`, `show $2` (289 lines) already shows date-only offline transit clearings,
and `select classify(m) -> "resend" where m.event_type == "clearing" && m.data.network_ref == "<ref>"` checks one
by one.

## Oracle

`oracle.py <dir>` runs `run_ledger.py --business-date D --spool hidden/<name>.jsonl.gz --out <tmp>` and compares the
settlement JSON with the generator's truth (`*.truth.json`). The truth is computed from the unique card events, not
from messages, and independently of the ledger code. It covers totals, counts, clearings per group, and every
card's movement and held amount.

| dataset | content | pristine |
|---|---|---|
| h1-original | the consumed queue (9,455 messages; 141 re-sends, 157 redeliveries, 280 identical offline fares) | FAIL |
| h2-commuters | 45 % riders (1,253 identical offline fares), 5 % re-sends (half before the original), 5 % redeliveries | FAIL |
| h3-redelivery-storm | 15 % redeliveries, 6 % re-sends (60 % before the original), 25 % out-of-order clearings | FAIL |
| h4-no-identical-fares | no two identical offline fares on a card (regression), 3 % re-sends | pass |

| work | result |
|---|---|
| pristine | FAIL (h1, h2, h3) |
| `fix.patch` | PASS |
| `wrong-fix-msgid.patch` (dedup by message id only) | FAIL on all four (re-sends double-posted) |
| `wrong-fix-offline.patch` (no fingerprint for clearings without an auth code) | FAIL on all four (offline re-sends double-posted) |

Grading takes about 2.5 s.

## Recording (`record.sh`)

`record.sh [WORKDIR]` copies the queue dump into a `mktemp` directory and records
`run_ledger.py --business-date 2026-09-28 --spool <tmp>/spool/… --out <tmp>/reports` with cwd=WORKDIR and
`PYTHONDONTWRITEBYTECODE=1`. It writes only `WORKDIR/report.pmdb`.

| measure | value |
|---|---|
| failing run | 0.4 s |
| recording | 5.6 s |
| trace | 50–56 MB, 308k observations, 57 functions |
| `query.pmdb` on the debug pmdb build | 7.6 s, including load |

The code was shaped for the recorder:
- module-level state for the dedup sets, holds, parking and postings;
- fee and MCC configuration installed once, instead of passing `settings` to every call;
- the batch loop inlined in `run`.

The first version passed `settings` (with its MCC table) to fee functions and recorded 98 MB. These choices don't
hint at the bug.

**Production vs recording:** production read the queue through `GatewayQueue`; the recording reads the same messages
in the same order through `SpoolQueue` (the trace shows `SpoolQueue.receive`). The log in `work/` is that run's log,
with timestamps shifted to Sep 29 04:10 UTC (durations ×40, as a gateway run takes longer), paths rewritten to
`/srv/cardledger/reports`, and the "reading … from dump" line removed (`gen/make_work_outputs.py`).

## Threats to fairness

- **Domain knowledge.** A model that knows card schemes may think of offline transit clearings (or of ARNs as the
  presentment identity) quickly. Then arm A can find the bug fast; this is the main risk to the scenario's
  discrimination.
- **The issue's numbers.** "202 cards, all debits, €808.30" averages €4 per card, suggesting small transactions. A
  real bank exception report would give this. We left out transaction counts: 280 missing clearings would give an
  average of €2.89, nearly naming fares.
- **`messages.py` documents** "auth_code (absent for offline transactions)". This is realistic, and it is the clue a
  careful reader needs.
- **The log** reports "(521 offline)" clearings and "421 processor re-sends". Neither is anomalous without a
  baseline.
- **Arm B can verify its fix against the trace,** e.g. by recomputing the clearings with `network_ref` dedup from
  the export, and so can see that it reaches 307,601.81. Arm A can't. This is the intended asymmetry of the
  post-mortem setting.
- **Trace size and query speed** (50 MB, ~8 s per query on the debug build) cost arm B time, not the reverse.

## Validation (`validate.sh`, all 13 steps PASS, 20 s)

1. The failing run on the private dump shows clearings 306,793.51 and net movement -219,382.54. The summary and the
   log in `work/` are that run's.
2. The oracle fails pristine work.
3. `fix.patch` applies. The fixed run shows clearings 307,601.81 (4,235) and net -220,190.84, and the oracle passes.
   Both wrong fixes fail the oracle.
4. `record.sh` writes `report.pmdb` (56 MB on disk) and nothing else. The `query.pmdb` + `query.py` output contains
   `query_expect.txt`.

## Regenerating the data (`gen/`)

```
python3 gen/gen_queue.py --seed 20260928 --cards 2400 --out private/card-events-2026-09-28.jsonl.gz
cp private/card-events-2026-09-28.jsonl.gz hidden/h1-original.jsonl.gz
cp private/card-events-2026-09-28.jsonl.gz.truth.json hidden/h1-original.jsonl.gz.truth.json
python3 gen/gen_queue.py --seed 7201 --date 2026-09-29 --p-rider 0.45 --p-resend 0.05 --p-resend-first 0.5 --p-redeliver 0.05 --out hidden/h2-commuters.jsonl.gz
python3 gen/gen_queue.py --seed 7202 --date 2026-09-30 --cards 2400 --p-rider 0.25 --p-resend 0.06 --p-resend-first 0.6 --p-redeliver 0.15 --p-ooo 0.25 --p-quick 0.4 --out hidden/h3-redelivery-storm.jsonl.gz
python3 gen/gen_queue.py --seed 7203 --date 2026-09-27 --distinct-offline --p-resend 0.03 --out hidden/h4-no-identical-fares.jsonl.gz
python3 gen/make_work_outputs.py
```

`private/card-events-2026-09-28.jsonl.gz.truth.json` holds the bank's figures for the issue.
