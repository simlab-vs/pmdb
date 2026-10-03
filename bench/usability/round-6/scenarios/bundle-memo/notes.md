# bundle-memo: a memo key that collides across regions (scenario kind 4)

## The program

`work/` is a quote engine (955 lines, 13 modules): `quote_run.py` prices the day's 800 open orders
(`data/orders.jsonl`) for 420 customers in 8 countries. It uses region price lists
(`data/catalog/pricelists/`), 11 bundle offers (3-for-2 mix-and-match, combos, bulk) and
VAT/shipping rules. `quoting/engine.py` finds the cheapest way to pay for a cart with a recursive
search over "pay the first unit singly, or as part of one offer application". The search
memoizes sub-carts in a module-level dict that lives for the whole run: 5,218 sub-carts searched
and 9,358 reused.

## The bug

The memo key is `(cart_key(cart), ctx.cache_key())`. `PricingContext.cache_key()` in
`quoting/context.py` returns `(currency, tier, channel, date)`. That was enough while every
currency had one price list. AT now has its own EUR price list (`eur-at`, 7 SKUs dearer), while
DE, FR, NL, BE and IE share `eur-standard`. A sub-cart priced first for an AT customer is reused
for a later DE or BE customer with the same tier and channel, and the reverse. Only 4 of 800
quotes are wrong:
- Q-30260 (DE) and Q-30457 (BE) are overcharged, and these are the ones customers complained
  about;
- Q-30409 and Q-30450 (AT) are undercharged, and nobody complains about those.

Q-30457's sub-cart `{TB-203: 3}` comes back with two units at the AT price (4.70) and one at the
standard price (4.20), because sub-results from different customers are mixed.

**Fix** (`fix.patch`): add `self.region` to `cache_key()`. Keying by price list id, clearing the
memo per quote, or dropping the memo also pass the oracle; without the memo the oracle takes 35 s.

**Why the faulty code looks plausible.** The method is called `cache_key`, and it looks
deliberately complete: four fields, leaving out only `customer`, which obviously shouldn't
split the cache. The same key also indexes the eligible offers, where it is correct. Nothing
in the method mentions prices. The price list is chosen in another module
(`catalog.unit_price` → `price_list_id(ctx.region)`).

## The issue and its decoys

Customer service reports two quotes whose subtotal after offers is higher than the shop's, while
their list price is right, and says both used the loose-tea 3-for-2. That points a reader at:
- the offers code: the mix-and-match enumeration and "free = cheapest";
- the search's optimality;
- rounding and VAT;
- the phone/store channel rule.

None of these is at fault. The output (`quotes.csv`) has totals only, no lines. The issue doesn't
mention Austria, price lists, or SKU TB-203.

## Why reading alone is hard, and what a strong reader would do

A reader has to connect three things:
1. Q-30457 is wrong only because of an earlier quote, through the memo.
2. The memo key comes from `context.py`.
3. Prices also depend on the region, through `catalog.price_list_id`.

None of the issue's words (3-for-2, subtotal, store pickup, Gent, Leipzig) greps to the cache key.

**Honest weakness.** `engine.py` is the central 100-line module, and its `_results` dict is in
plain view. A strong reader who asks "is this memo key complete?" will compare it with what
`unit_price` reads and find the missing region in about 5 files. That takes perhaps 6–10 turns
for Opus. So this scenario rewards runtime evidence less than the post-mortem or intermittent
ones. Its resistance depends on the reader not putting the cache first among several plausible
suspects.

## How an agent without pmdb would likely proceed

- **Rerun.** The run is cheap (0.4 s) and deterministic, so the symptom reproduces at once.
- **Isolate.** The natural next step is to price only the two orders: `--only Q-30260 Q-30457`, or
  an orders file with just those lines. Alone, both give the shop's totals (72.11, 54.57). That's
  the key clue: the result depends on the other orders, which points to shared state, i.e. the
  memo. A strong agent then reads the key and finds the region missing. Expected: 8–15 turns.
- **Weaker path.** Print the lines of the search for one quote, see TB-203 at 4.70 next to 4.20,
  grep the price lists for 4.70, and find `eur-at`. Then wonder how an AT price gets into a BE
  quote, and bisect the orders. That takes several print/rerun cycles, each cheap.

## How pmdb shortens it (query.pmdb)

```
select best_price(cart, ctx) -> p where ctx.customer == "C-1054"
show $0
select unit_price("TB-203", ctx) -> u where u == 470
show $1
```

Output (trimmed):

```
$0 = <5 element(s) in 1 trace(s)>
quote.py:30:  call best_price({LT-105: 2, LT-111: 1, TB-203: 3}, {..., customer: C-1054, region: BE, tier: retail}) -> {lines: [{amount: 2660, offer: TEA-3FOR2, ...}, {amount: 470, ...TB-203}, {amount: 470, ...TB-203}, {amount: 420, ...TB-203}], total: 4020}
...
engine.py:..: call best_price({TB-203: 3}, {..., customer: C-1054, region: BE, ...}) -> {lines: [{amount: 470, ...}, {amount: 470, ...}, {amount: 420, ...}], total: 1360}
$1 = <5 element(s) in 1 trace(s)>
engine.py:..: call unit_price(TB-203, {channel: web, currency: EUR, customer: C-1295, date: 2026-09-30, region: AT, tier: retail}) -> 470
```

1. The first query shows one BE result pricing the same SKU at two prices.
2. The second shows that 4.70 was only ever computed for an AT customer, C-1295 (Q-30409, an
   earlier quote).
3. Together they say: a result computed for AT was reused for BE. The memo key then explains
   it, and the fix follows.

That is 2–3 pmdb invocations and no edits or reruns, but each query takes about 15 s on the
47 MB trace. `show functions` lists `best_price`, `unit_price` and `PricingContext.cache_key`,
which also points at the key.

## Threats to fairness

- **The isolation experiment is cheap and decisive for arm A too** (pricing the order alone gives
  the right total). pmdb mainly saves the step from "it's shared state" to "which state, and from
  which earlier quote".
- **The trace is large** (about 375k observations, 47–53 MB) and each query loads it in about
  15 s. An agent that runs many exploratory queries pays for that.
- **The code was shaped so that recording works.** The catalog and the engine are module-level
  state instead of objects. Otherwise the recorder pickles `self` on every call: the first
  version's recording grew to over 4 GB of memory. `quote_order` takes one customer row, not the
  customers dict. This is legitimate style, but it was chosen for recordability.
- **Data generation is outside `work/`** (`gen/gen.py`), so the agent doesn't see which SKUs
  differ in AT except by reading the price lists.

## Numbers

- **Failing run:** 0.4 s.
- **Recording** (`record.sh`): 13–21 s; about 375k observations; 47–53 MB.
- **pmdb query:** about 15 s each, mostly loading the trace.
- **Oracle:** about 3 s. It runs four datasets (the original, and hidden h1–h3) and compares
  every row of `quotes.csv` with the reference fix's output:
  - h1 and h3 use other seeds (4 and 14 wrong quotes);
  - h2 gives BE and FR their own lists and leaves AT on the standard one (23 wrong quotes), so
    a fix that special-cases AT fails.

## Validation (`validate.sh`, all PASS)

1. Failing run: Q-30260 = 72.59, Q-30457 = 55.78 (the issue's numbers).
2. Oracle FAILS on pristine work (original: 4 wrong; h1: 4; h2: 23; h3: 14).
3. After `fix.patch`: 72.11 and 54.57; the oracle PASSES. The alternatives (key by price list
   id, clear per quote, no memo) also pass.
4. `record.sh` writes `report.pmdb` and nothing else (`diff -r` shows only it). The query output
   contains both lines of `query_expect.txt`.
