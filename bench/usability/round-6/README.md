# Usability study of pmdb, round 6 (exploratory): scenarios built for runtime evidence

**These scenarios were designed to favour runtime evidence.** In rounds 1–5, failing tests or
output diffs pointed straight at the cause, and Opus fixed bugs in about 6 turns by reading,
without runtime evidence. pmdb helped only when tests couldn't run. Round 6 asks whether pmdb helps
at all when evidence from the run is what's missing. It is an existence test of *where* pmdb can
help, not an unbiased estimate of how often it helps on real bugs. The bugs, data and issues were
hand-crafted, and adjusted iteratively so that reading alone is costly.

## Arms

- Both arms get `work/` (as `/work`) and `issue.md`.
- Arm B also gets pmdb, the pmdb skill and `/work/report.pmdb`, a trace of the failing run
  recorded by the scenario's `record.sh`.
- The agent may run the program, write inputs and add prints, except where the scenario prevents
  it (the post-mortem has no input; the planner's run takes minutes).

## Scenarios (`scenarios/<name>/`)

| # | Kind | Name | Program | Bug | Decisive pmdb query |
|---|---|---|---|---|---|
| 1 | Needle in a haystack | `billing-needle` | Electricity billing: 3,100 accounts, 3 meter-operator feeds; 898 lines | One exchanged meter's old readings come under a legacy id. Readings are merged in order of raw id, but settled per resolved id with flush-on-key-change, so the account is settled twice and the second bill overwrites the first. The total is 77.7 kWh short. | `select account_consumption(k, rs, _) -> c where c > 77.65 && c < 77.75`, then the same account's two calls |
| 2 | Post-mortem without the input | `refund-postmortem` | Payout reconciliation over a private webhook export; 816 lines | NovaPay's new API sends a refund lifecycle (pending → succeeded/failed, same refund id). Each event is booked as a refund. The export is never given; the agent has the log and the report. | `select /Ledger\.apply_refund/(_, _, t) where t.status != "succeeded"`, and one refund's events |
| 3 | Aliasing / mutation over time | `shared-tiers` | SaaS invoicing, 1,190 invoices, shared plan tiers; 873 lines | A rarely used upgrade advisor orders tiers with `util.ranked`, which sorts in place, reversing the shared tier list. Later Scale invoices are charged at the top-tier rate. | `select volume_charge(q, ts) where ts[0].start > 0` (arguments as at call time), then `ranked(...)` |
| 4 | Recursion / memoization | `bundle-memo` | Bundle-offer quote engine, 800 carts, recursive search with a run-wide cache; 955 lines | The cache key `PricingContext.cache_key()` omits the region. AT has its own EUR price list, so sub-cart prices leak between AT and DE/BE quotes. | `select best_price(cart, ctx) -> p where ctx.customer == "C-1054"` and `select unit_price("TB-203", ctx) -> u where u == 470` |
| 5 | Intermittent (hash seed) | `hashseed-intermittent` | Static site generator with plugins ordered topologically, ready set popped; 1,204 lines | A single-name `after = heading-ids` is parsed as a string and turned into a tuple of characters, so the constraint is silently dropped. On 7.6 % of `PYTHONHASHSEED`s the TOC runs before heading ids exist and every link is `#`. | `select load_manifest(path, _) -> spec where spec.name == "toc"` (shows `after: [h, e, a, d, …]`) and `order_plugins(...) -> order` |
| 6 | Expensive run | `slow-planner` | Route planner, 1,200 stops, local search with 5 move types; 996 lines; a run takes 2–3 min | When a relocate move empties its source route, the source route is released before the target is refreshed. Later routes shift down, so the wrong route's cached load is refreshed, and a later move overloads T-44. | `select apply_move(p, mv) -> rs where rs.all(s => s.vehicle != mv.v2)` |

Each scenario directory holds:
- `work/`: what the agent sees;
- `issue.md`: the symptom only;
- `fix.patch`: the reference fix (`patch -p1 -d <dir>`);
- `oracle.py <dir>`: hidden inputs plus the original case, exit status 0 for pass;
- `record.sh [WORKDIR]`: writes `WORKDIR/report.pmdb` and nothing else;
- `query.pmdb` with `query_expect.txt`;
- `notes.md`: rationale, the likely approach without pmdb, threats to fairness, timings;
- `validate.sh`;
- `gen/`: the data generators;
- `hidden/`: the oracle's data;
- `private/`: scenario 2 only, the job's input, which the agent never sees.

`validate_all.sh` runs every scenario's `validate.sh`. Each one checks that:
- the symptom reproduces;
- the oracle fails the pristine program;
- with `fix.patch`, the oracle passes;
- `record.sh` writes the trace and changes nothing else;
- the query output contains the expected lines.

## Known weaknesses (details in each `notes.md`)

- **The arms have the same capability.** Arm A can still find most bugs: per-account
  reconciliation scripts (1), running single quotes (4), sweeping seeds (5: the first failing seed
  is 39, about 20 s of builds), asserting cache invariants on a small day (6). pmdb should save
  turns, not make fixes possible. Only scenario 2 withholds runtime evidence from arm A.
- **Reading resistance was not screened.** The builders estimate that a strong reader finds the
  bug in about 6–10 turns (4) and 8–20 turns (others). Round 3 showed such estimates can be
  optimistic.
- **Issues give leads.** For example, the shared-tiers issue observes that the 50M+ rate was
  applied.
- **The code was shaped for the recorder.** pmdb-record pickles every object argument
  (including `self`) on every call. Early versions of scenarios 1, 2 and 4 produced 2–11 GB traces
  or stalled, and were restructured: module-level state instead of objects, dicts and NamedTuples
  instead of dataclasses. That is a finding about pmdb, and makes the code less typical.
- **Traces are large** (21–84 MB). Loading takes 1–15 s per pmdb invocation, and regex queries
  take up to 40 s on scenario 2.
- **pmdb problems found while building:**
  - a line holding only a `# comment` fails with "expected command";
  - `load` is a keyword, so a field named `load` can't be read (`s.load`).
