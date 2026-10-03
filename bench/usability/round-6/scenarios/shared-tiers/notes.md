# Scenario 3: shared-tiers (aliasing / mutation over time)

## The program and the bug

`work/` is a monthly usage-invoicing run for a SaaS company (873 lines, 15 modules in
`invoicing/` plus `run_invoices.py`): price catalog with graduated/volume/per-unit tiers,
usage aggregation from 121k daily metering records, enterprise contracts with committed
volumes and shortfall lines, prorated base fees on plan changes, discounts, FX, VAT, and
plan-upgrade notes. It writes 1,190 invoices.

The catalog is loaded once and every customer's pricing reads the same tier lists
(`plan["metrics"][m]["tiers"]`). Tiers are `NamedTuple`s, sorted by `start` at load.

**Bug.** `advisor.best_rate_reached` orders the tiers by price with the shared helper
`util.ranked`:

```python
by_price = ranked(tiers, key=attrgetter("unit_price"))
```

`ranked` reads like `sorted` (it returns the ordered list), but it sorts **in place**. The
advisor runs only for self-serve customers whose API volume reached the top tier of their
plan, to quote the next plan's rate, and it passes the *next* plan's tier list. In the
September data this happens once, for Growth customer C11044 (invoice 1036 of 1,190). From
then on the Scale plan's API tiers are ordered by descending volume, and `volume_charge`
(correct for ascending tiers) charges every later Scale customer the 50M+ rate of 0.0003.
That gives 26 wrong invoices (−50% to −63% on the API line), plus shortfall lines of two
contract customers. Customers processed before, and every other line and plan, are right.

**Fix** (`fix.patch`): `sorted(...)` instead of `ranked(...)` in `best_rate_reached`.
Making `ranked` non-mutating also passes the oracle (all of its other callers use its
return value).

## Why reading alone is hard

- The symptom (the issue) points to the API line of Scale invoices and to the volume pricing,
  which is correct. Nothing in the symptom mentions Growth customers or upgrade notes.
- The faulty line looks like the idiomatic `sorted(...)` call; the mutation lives in a generic
  helper in another module, called from 5 places, 4 of them on local lists (the billing order,
  the catalog at load, plan-change histories, the summary's largest invoices).
- The trigger is a property of the data: one Growth customer with 8.2M requests (above
  Growth's 5M top tier) in 1,200 customers. A reader can't tell from the code when, or whether,
  the advisor runs.
- Red herrings a reader will likely check first: contract discounts and shortfalls (the same
  metric, the same plan), the customer discount line, FX conversion (one named invoice is in
  GBP), included units, prorated plan changes.

What a strong reader would likely do: compute 2,192.01 / 7,306,714 = 0.0003, conclude that the
top tier was picked, and so that the tiers were out of order for these customers. Then the
question is who reorders a shared list: `grep sort` finds only `util.ranked` (and `sorted`
calls), and checking `ranked`'s 5 callers finds the advisor. **This is the scenario's main
weakness**: a reader who forms the "the shared tier list was reordered" hypothesis can confirm
it in a few greps. The hypothesis requires noticing that `volume_charge` depends on order *and*
that the list is shared; we expect it to take a reader roughly 10–20 turns, not 5.

## How an agent without pmdb would likely proceed

1. Run the program (2 s), confirm the named invoices are wrong.
2. Check `volume_charge`/`price_metric` by hand for C11055: correct with the catalog's tiers.
3. Re-run with prints in `volume_charge` for the named customers (or pdb with a conditional
   breakpoint) and see the tiers in descending order, then add a print/assert where the order
   first breaks (e.g. assert `tiers[0].start == 0` in `volume_charge`) and walk back to the
   previous customer's invoice, or grep for sorting. Each rerun is cheap (2 s), so the cost is
   in turns and edits, not wall time: 3–6 extra turns after the hypothesis.
4. Alternatively, bisect the customers file (run subsets) to find that the error depends on
   which customers came before; possible but slower.

## How pmdb shortens it

Arguments are recorded at call time, so the reordering is visible directly (`query.pmdb`):

```
select volume_charge(q, ts) where ts[0].start > 0
show $0
select best_rate_reached(ts, u)
show $1
select ranked(items, **) where items.len() == 4 && items[0].has("unit_price")
show $2
```

Output (abridged):

```
$0 = <29 element(s) in 1 trace(s)>
invoicing/pricing.py:41: call volume_charge(1017477, [{start: 50000000, unit_price: 0.0003, upto: none}, …, {start: 0, …}]) -> 305.24
…
$1 = <1 element(s) in 1 trace(s)>
invoicing/advisor.py:39: call best_rate_reached([{start: 0, unit_price: 0.0008, …}, …, {start: 50000000, unit_price: 0.0003, upto: none}], 8239835) -> {start: 2000000, unit_price: 0.0006, …}
$2 = <2 element(s) in 1 trace(s)>
invoicing/catalog.py:61: call ranked([{start: 0, …}, …], key: <object>) -> [{start: 0, …}, …]
invoicing/advisor.py:20: call ranked([{start: 0, unit_price: 0.0008, …}, …], key: <object>) -> [{start: 50000000, unit_price: 0.0003, upto: none}, …]
```

A natural route for an agent: `select volume_charge(q, ts) -> r` for a named customer's
quantity shows reordered tiers; `where ts[0].start > 0` gives all 29 such calls, the first
for C11047 (invoice 1039). `pmdb --show report.pmdb | grep -n "call build_invoice\|ranked\|best_rate\|call volume_charge"`
around that point shows the previous invoice (C11044) calling `best_rate_reached` →
`ranked` on the in-order tiers, which returns them reversed. That is 3–4 pmdb invocations,
with no edit or rerun of the program.

## Fairness threats

- See "Why reading alone is hard": a hypothesis-driven reader can find it with grep. Reruns are
  cheap (2 s), so prints/asserts are an affordable alternative; pmdb's advantage here is in
  turns, not wall time.
- The issue gives the computed "should be" amounts and the remark that 0.0003 seems to apply,
  as a careful billing analyst would; this helps both arms equally and points at tier
  selection (deliberately, so the symptom leads to the correct pricing code).
- The named invoices are all late in the run, and the one cited as correct is earlier
  (INV-0263). An agent may infer order dependence from the numbers; that's realistic.
- A defensive fix that re-sorts tiers inside `volume_charge` also passes the oracle, since the
  oracle grades behaviour. Upgrade-note texts aren't graded.
- Trace size is 21 MB, mostly from per-invoice arguments (customer dicts, plans); `show $0`
  lines are long (use `clip`).

## Numbers

- Failing run: `python3 run_invoices.py data --period 2026-09 --out out`, ~2 s.
- Recording (`record.sh`): ~6 s, 107,949 observations, report.pmdb ≈ 21 MB.
- Oracle: ~12 s; original data + 3 hidden datasets generated by `gen/make_data.py`
  (an early Growth upgrade; a Starter upgrade, which reorders Growth's tiers; several
  upgrades and 9 contracts). The bug changes 26, 87, 282 and 225 invoices respectively in the
  original and the hidden datasets, so a data-specific patch fails.

## Validation (`validate.sh`, all PASS)

1. The failing run on pristine work: INV-2026-09-1047's API line is 2,192.01 (the issue's
   symptom); INV-2026-09-0263 is 1,405.38 (correct).
2. Oracle on pristine work: `FAIL original: 26 of 1190 invoices differ, first INV-2026-09-1039`.
3. With `fix.patch`: INV-2026-09-1047's API line is 4,384.03; oracle `PASS all 4 datasets`.
   The alternative fix (non-mutating `ranked`) also passes.
4. `record.sh` on a temp copy writes report.pmdb (21–22 MB) and changes nothing else;
   `query.pmdb`'s output contains every line of `query_expect.txt`.

## pmdb issue found while building

A line holding only a comment (`# …`) makes pmdb fail with `Error: expected command` when
commands come from stdin, although the README says comments extend to the end of a line.
A trailing comment after a command works. `query.pmdb` therefore has no comment lines.
