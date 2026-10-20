# slow-planner: an expensive run (scenario kind 6)

## The program

`work/` is a daily delivery route planner (`plan_day.py` and the package `routeplan`, 996 lines
of Python in 9 modules, standard library only). It reads one day's orders (1,200 stops with
weights, service times and optional delivery windows) and a mixed fleet (1,000 kg vans and
1,600 kg trucks), and:

1. builds the travel matrices (`instance.py`) and initial routes by the savings method
   (`construct.py`);
2. improves them by a descent over five neighbourhoods (`moves.py`: relocate, swap, segment
   move, tail exchange, 2-opt), applying the best move found (`apply.py`), restarted 60 times
   from partly ruined and recreated plans (`search.py`);
3. tries to take the lightest routes out of service (`search.reduce_fleet`);
4. rechecks the final plan from scratch and writes the dispatch sheet and summary
   (`report.py`), exiting 1 if there is a problem.

The run is pure CPU: **2-3 minutes** for the reported day (117-191 s measured, depending on
the other work on the machine).

## The bug

`Plan` keeps `stats[r]`, the cached totals (load, distance, cost) of route `r`, and every scan
checks a receiving route's capacity against `plan.stats[r2].load_kg`. `apply._relocate`, the
only operation that can empty a route, does this when the moved stop was the last of its route:

```python
    if src:
        changed.append(plan.refresh(mv.r1))
    else:
        plan.release(mv.r1)
    changed.append(plan.refresh(mv.r2))
```

`Plan.release` takes the emptied route out of the active prefix of `plan.routes` (pop and
append, "keeping the other routes in order"), which shifts every later route down by one. When
the receiving route came after the emptied one (`r2 > r1`), `refresh(mv.r2)` refreshes the
route *after* it, and the receiving route keeps its old totals, which lack the stop it just
received. The next move into that route passes the capacity check against the stale load and
overloads the vehicle. Usually a later move touching the route refreshes it, so the effect is
transient. Only when the overload survives the rest of the search (about 1 day in 8 for this
generator) does it reach the final plan, as here: `T-44 carries 1614 kg, capacity 1600 kg`.

The fix (`fix.patch`) refreshes the receiving route before releasing the emptied one. Adjusting
the index (`r2 - 1`) or refreshing by route object works equally well (checked: the oracle
passes on the index-adjusting variant).

Why it looks plausible: release-then-refresh reads naturally ("drop the empty route, update
the other one"), the index shift is hidden in `Plan.release` in another module, every other
operation refreshes by index too, and the cached totals are a standard optimisation. The
symptom (one overloaded vehicle at the end of a 3-minute search) names neither `apply.py` nor
`plan.py`.

## Why reading alone is hard, and what a reader would likely suspect first

- The issue points at capacity, so a reader first checks the capacity tests in the five scans
  (`moves.py`), in `recreate` and in `cheapest_insertion`. All of them are correct given
  correct cached totals. `best_tails` even computes loads from scratch.
- Next suspects: the segment move with reversal, the tail-exchange index arithmetic, `swap`'s
  two-sided check, `open_route`, the vehicle assignment in `Plan.from_sequences`, and the
  final check in `report.py` (e.g. an off-by-one in a load sum).
- To find the cause, a reader has to form the hypothesis "the cached totals of the receiving
  route are stale", then audit every place that changes stops against every place that
  refreshes, and notice that `release` renumbers routes. That is feasible: a strong reader who
  suspects stale caches could find it in perhaps 10-20 tool calls. Reading alone can't confirm
  it, though. The failure needs a relocation that empties a route with a lower index than the
  receiving route, followed by an insertion into that route before any other move touches it,
  followed by no repair for the rest of the search.

## Without pmdb

- **Re-running the reported day** costs about 3 minutes per print-and-rerun cycle. A useful
  print (e.g. checking `stats` against `route_stats` after every move) needs a first run to
  find the first divergence and more runs to narrow it down.
- **pdb** is hard to use here. The interesting move is one of ~4,400 applied moves, deep in the
  60th restart, and conditional breakpoints need the hypothesis first.
- **Smaller inputs.** The agent has no generator, but could write one or subsample the given
  day. Small days (300 stops, `--rounds 8 --neighbours 24`) plan in ~3 s, but only about 1 in
  8 random days shows a final overload (the oracle's hidden days were selected for it). A
  smaller input that reproduces is therefore reachable by a script looping over random days.
  An assertion of `plan.stats == route_stats(...)` after every `apply_move` reproduces on
  almost any day, since the stale totals occur ~30 times per full run, even without a final
  overload. An agent that thinks of that invariant finds the cause quickly without the trace.
  This is the main threat to the scenario's "expensive" premise.

## With pmdb (arm B gets `report.pmdb` of the reported run)

`query.pmdb`:

```
select apply_move(p, mv) -> rs where mv.v1 == "T-44" || mv.v2 == "T-44"
show $0
select apply_move(p, mv) -> rs where rs.all(s => s.vehicle != mv.v2)
show $1
```

The first query lists all 36 moves touching T-44, with the totals `apply_move` returned. Among
them is the relocation of S0259 into T-44 whose returned totals belong to **T-45**, and later
the relocation of S1170 into T-44 that returns `load_kg: 1614` on a 1,600 kg truck, i.e. a move
accepted past capacity. The second query generalises: 38 relocations (of 4,407 applied moves) whose result
doesn't include the receiving vehicle. All have `r2 > r1`, all emptied their source route (their result
has no entry for it), and 9 return the totals of an empty, idle route. Excerpt:

```
routeplan/search.py:29: call apply_move(Plan(2026-09-28, 104 routes), {gain: 97.8699, i: 0, j: 13,
  kind: relocate, length: 1, r1: 20, r2: 41, reverse: false, stop: S0259, v1: T-22, v2: T-44})
  -> [{capacity: 1600, cost: 133.27, distance: 77.851, duration: 362.9, load_kg: 1313, stops: 18,
  vehicle: T-45}]
```

From there `_relocate` (the operation the call dispatches to) and `Plan.release` are a short
read. A natural first query, `select apply_move(p, mv) -> rs where rs.any(s => s.load_kg >
s.capacity)` (13 matches), shows the overloading move itself, after which the T-44 history query
above is the obvious next step. Each query takes 3-6 s on the 84 MB trace.

## Measurements

- Failing run (plain): 117-191 s depending on machine load (other scenarios were being built
  in parallel), exit status 1, `problems: 1  capacity: T-44 carries 1614 kg, capacity 1600 kg`.
- Recorded run (`record.sh`): 143-193 s. Recording adds almost nothing, because the heavy work is
  inline loops. 522,739 observations, **84 MB**. Most observations are `schedule_ok` calls
  (feasibility checks of improving candidates); the matrices are memoryviews, which can't be
  pickled, so the recorder stores the large `Instance`/`Plan` objects as their short `repr`.
- Fixed run: 185 s, `problems: 0`, 90 vehicles, cost 8552.78 (vs 8542.68 overloaded).
- Oracle: ~7-8 s (8 hidden days of 300-450 stops in parallel, 6 of which overload without the
  fix, plus an invariant check on one day).

## Oracle

`oracle.py DIR` plans 8 hidden days (`hidden/`, generated by `gen/make_day.py` with other
seeds; the unfixed planner overloads a vehicle on 6 of them, and 2 are controls). For each, it
checks the dispatch sheet independently of the planner's own check: each stop served exactly
once, capacities, windows and shifts, and a cost at most 1% above the reference fix's
(`hidden/expected.json`, made with `--make-expected`). It then runs one hidden day with
`search.apply_move` wrapped to compare the cached totals with recomputed ones after every move.
That fails a symptom-level fix (e.g. recomputing loads in the capacity checks but leaving the
cache stale, which passes the plan checks; tested). If the agent restructured those internals,
the invariant check is skipped with a note. `--full` also plans the original day (~3 min).

## Threats to fairness

- **Reachable by reasoning.** The stale-cache hypothesis is a standard suspicion for "a
  constraint the search is supposed to enforce is violated". Opus may get to `release` by
  reading (see above).
- **Cheap reproduction exists.** The invariant assertion, or small generated days, avoid the
  3-minute rerun. The scenario favours pmdb only as long as the agent first tries to work from
  the reported run.
- **Arm B's trace is large** (84 MB; `show` of all moves touching a vehicle prints ~15 KB).
  Unfiltered `pmdb --show` would be enormous (hundreds of MB of text), which could cost arm B
  turns.
- **The overload is small** (14 kg over 1,600 kg). The planner itself flags it, so the symptom is
  unambiguous, but an agent might suspect rounding or data first.
- **pmdb usability problems** met while building this (not part of the design, but they would
  hit agents too):
  1. `load` is a keyword (the `load … as` command), so `s.load > s.capacity` fails with
     `error: expected identifier`. The field was named `load_kg` to keep the decisive query
     writable; a real program with a `load` field would trip agents.
  2. A line containing only a comment (`# ...`) fails with `error: expected command`, although
     the README says comments extend to the end of a line. Trailing comments after a command
     work.

## Validation (validate.sh)

Last run of `validate.sh` (all steps PASS, exit 0; 8 minutes):

```
PASS fix.patch applies
PASS (1) failing run shows the symptom (117 s)
PASS (3a) fixed run has no problems (118 s)
PASS (2) oracle fails on pristine work: FAIL: d300_108: T-03 carries 1676 kg > 1600 kg (1 problems); d300_117: ...
PASS (3b) oracle passes on fixed work: PASS: 8 days planned without problems, costs within 1% of the reference
PASS (4a) record.sh (143 s, 89 MB)
PASS (4b) record.sh leaves no other changes
PASS (4c) query.pmdb runs
PASS (4d) query output contains query_expect.txt
```

Also checked:
- `oracle.py <fixed> --full` passes, including the original day (104 s).
- On pristine work, the oracle fails on all 6 bug days.
- An alternative correct fix (index adjusted after `release`) passes.
- A symptom-level fix (loads recomputed in the capacity checks, cache left stale) fails on the
  invariant check.
- The fixed planner reported `problems: 0` on all 64 random small days tried while searching
  for hidden days, so no other defect produces violations.

Run times vary with machine load: plain runs took 117-191 s and recorded runs 143-193 s while
five other scenarios were being built on the same 14 cores.
