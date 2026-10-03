# stock-allocation: notes

**Kind:** post-mortem of a run that depended on external state that has changed since. The nightly allocation job
read stock levels from the inventory service, which only knows current levels. The agent gets the code, the night's
OMS export (`input/`), the job's INFO log and its summary, and the issue. It never gets the levels the service
returned at 02:00. Arm B also gets `report.pmdb`, a trace of that run.

## The program (`work/`, 1,012 lines of Python in 13 modules, plus config, catalog, input, log and summary)

`allocate_night.py` allocates one night's open order lines (2,700 orders, 5,123 open lines; webshop, marketplace,
B2B) to four warehouses and writes a pick list per warehouse and a summary. Modules: settings, catalog (SKU
attributes, kits), orders (OMS export reader, filters, multipacks, allocation order), inventory (service client with
paging and retries, or a `--levels-file` dump; `available = max(0, on_hand - reserved)`, 0 for locations under
count or blocked), ledger (stock left during the run, module state), routing (country routes, hazmat/bulky
capabilities), policy (safety-stock protection for marketplace lines), allocator (split, ship-complete, kits),
checks, pick lists (waves, bins), summary.

## The bug

`allocator.allocate_split`:

```python
        take = min(need, policy.allocatable(line.sku, warehouse, line.channel))
        if take:
            ledger.reserve(line.sku, warehouse, take)
            picks.append(Pick(warehouse, line.sku, take))
            need -= take
```

`policy.allocatable` returns the stock left minus the safety stock for marketplace lines, which is **negative**
when a location holds less than its safety stock. `if take:` is true for a negative number, so:
- the line gets a negative pick at that warehouse;
- `ledger.reserve` with a negative quantity *raises* the warehouse's remaining stock (phantom stock), and its guard
  (`qty > free`) doesn't object;
- `need` grows, so the next warehouse in the route is asked for the ordered quantity plus the safety stock gap.

Effects: the next warehouse packs too many units for the marketplace line (over-shipping), and later lines take the
phantom stock at the first warehouse (short picks). After the phantom stock is consumed, the next marketplace line
for that SKU repeats it. Every check passes: the ledger never goes negative, and each line's picks add up to the
ordered quantity minus the backorder. The pick-list writer merges rows and drops non-positive ones, so the negative
lines never reach the WMS. In the private state 152 of 2,512 locations start below their safety stock, and more fall
below it during the run: 143 negative `allocatable` results, 116 lines with a negative pick.

**Fix** (`fix.patch`): `if take > 0:`. Clamping `allocatable` at 0 is equivalent.

**Why the faulty code looks right.** `if take:` reads as "skip warehouses with nothing to give", which is what it does
for every location at or above its safety stock. The client visibly clamps `available` at zero, which suggests
stock is never negative. The ledger guards against over-reservation, and the checks state "no stock promised twice,
every unit allocated or backordered" and pass. Negative stock arises only from the policy subtraction, in another
module, and only for locations whose state (available < safety stock) is in the service's data.

## Why code + log alone are hard

The log gives per-warehouse totals only. The issue's symptoms (short picks, over-shipped marketplace lines, all
checks passed) admit many explanations a reader can't test without the levels:
- the multipack conversion (`qty × pack_size`; one example in the issue is a 3-pack, a deliberate red herring:
  the conversion is correct);
- kits (component quantities), ship-complete B2B lines;
- statuses (`counting`, `blocked`) and the clamp of `on_hand - reserved`;
- paging in the service client (duplicate or missing pages), `two levels for` guard;
- duplicate OMS lines, express-first ordering, wave merging in the pick-list writer;
- the inventory service having been wrong (the issue says the counts confirmed it).

**What a strong reader would likely try first.** All over-shipped orders are `M-` (marketplace), which leads to the
only marketplace-specific code: the multipack conversion and the safety-stock policy. A reader who asks "can
`allocatable` be negative, and what does the loop do then?" finds the bug. That's the main weakness: the path is
short once the channel is noticed.

## Arm A (without the trace): a viable route

The orders are in `input/`, and the job accepts `--levels-file`, so arm A can run the night (0.15 s) against levels
it invents. Generous levels reproduce nothing; levels with locations below their safety stock reproduce both
symptoms (e.g. M-882837 with HM-1128 at 2 below safety in LEJ). Comparing pick lists with the orders shows
over-shipped marketplace lines. Reasoning alone also works: over-shipping a line means its picks exceed `qty`
while the check says picks = qty − backorder, so some pick must be negative. Expect 10–25 turns.

## Arm B (with the trace): how pmdb shortens it

The trace has every `allocate_line(line) -> allocation`, every `allocatable(sku, wh, channel) -> free`, and the
service's pages (`_get_json(url, timeout) -> {levels: [...]}`, `to_level(record) -> Level`). The natural first query
from the issue is the named order:

```
select allocate_line(l) -> a where l.order_id == "M-882837"
show $0
```

which shows `picks: [{qty: -10, sku: HM-1128, warehouse: LEJ}, {qty: 11, sku: HM-1128, warehouse: RTM}]` for an
ordered quantity of 1. `query.pmdb` then counts the cause:

```
select allocatable(sku, wh, channel) -> free where free < 0
select allocate_line(l) -> a where a.picks.any(p => p.qty < 0)
export $2 to "negative.jsonl"
```

and `query.py` aggregates: 116 lines with a negative pick, all marketplace; negative units LEE 28, LEJ 250, MAD 17,
RTM 191. Expect 3–8 turns.

## Oracle

`oracle.py <dir>` runs the agent's job with `--levels-file` on four hidden nights and compares the pick lists
(units per order, line, SKU and warehouse) and the summary's backorders with `gen/reference.py`, an independent
implementation of the README's policy. It also reports pick rows with non-positive quantities and locations picked
beyond their stock. About 1.5 s.

| night | content |
|---|---|
| h1-original | the failing night (work's orders, the private levels) |
| h2-low-stock | 3,000 orders, scarce stock, 393 locations below safety stock |
| h3-marketplace-kits | 50% marketplace orders, 10% kit lines, 40% express |
| h4-ample-stock | no location below safety stock and plenty of stock (regression: passes pristine too) |

Checked: pristine FAIL (h1–h3); reference fix PASS; `wrong-fix.patch` (the ledger ignores non-positive
reservations, which stops the short picks but not the over-shipping) FAIL (h1–h3).

## Recording (`record.sh`)

Production read the levels from `https://inventory.prod.internal:8443/v2`. `record.sh` puts `gen/service` on
`PYTHONPATH`: its `sitecustomize.py` answers HTTPS requests to that host from the private snapshot, with the
service's paging. So the trace shows the job calling the production URL, as it did, and nothing from `gen/` is
recorded. The orders are copied to `<tmp>/oms/exports/open-lines-2026-09-29.jsonl`.

| measure | value |
|---|---|
| failing run | 0.15 s |
| recording | 5.5 s |
| trace | 36–42 MB (depends on the work path), 249k observations, 52 functions |
| `pmdb show functions` | about 6 s (debug build) |
| `query.pmdb` | about 7 s |

## Threats to fairness

- **The channel is visible.** The over-shipped orders are all `M-`, and the README states the marketplace
  safety-stock rule. This is realistic but shortens arm A's path a lot (see above).
- **The issue no longer mentions low stock after a sale.** An earlier draft did, and the line was removed as a hint that low stock matters.
- **Arm A can replay with invented levels.** Intended: arm A must not be hopeless. The scenario tests whether the
  trace saves the hypothesis search, not whether the fix is reachable.
- **Short picks have two causes in principle** (phantom stock vs. wrong levels); the issue rules out the second.
- **The log has no hint of negatives**, but the per-warehouse "units" in the summary are net (they subtract the
  negative picks), so they are lower than the pick lists' totals. The user doesn't have the pick lists.

## Validation (`validate.sh`, all PASS, about 15 s)

1. The production-like run (`gen/production_run.sh`: service answered from the snapshot, log rewritten to
   2026-09-29 02:00 and `/srv/...` paths) writes exactly `work/logs/` and `work/reports/` (log compared without
   timestamps). Its pick lists give the issue's numbers: Leipzig 127 units short over 18 SKUs, Rotterdam 82 over
   19, Leeds 1; 335 units over-shipped on 79 lines of 77 orders (`gen/symptoms.py`); M-882837 line 1 gets 11 units
   from Rotterdam.
2. The oracle fails on pristine work.
3. `fix.patch` applies; the fixed run has no short picks and no over-shipping; the oracle passes; the oracle fails
   `wrong-fix.patch`.
4. `record.sh` writes `report.pmdb` and changes nothing else; the query output contains `query_expect.txt`.

## Regenerating the data

```
sh gen/regenerate.sh            # orders, private levels, hidden nights and their reference truth
sh gen/regenerate.sh --catalog  # also the catalog (seed 4401)
sh gen/production_run.sh work work   # the log and summary in work/
```

`gen/regenerate.sh` lists the seeds and parameters (failing night: seed 20260929, stock scale 1800, 8% of locations
below safety stock).
