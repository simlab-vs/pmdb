# Allocation of 29 September: short picks in Leipzig and Rotterdam, marketplace orders packed with too many units

The nightly allocation ran as usual on 29 September at 02:00:

```
cd /srv/allocation && python3 allocate_night.py --orders /srv/oms/exports/open-lines-2026-09-29.jsonl --date 2026-09-29 --log logs/allocation-2026-09-29.log
```

Its log and summary are in `logs/` and `reports/`, and the OMS export it read is in `input/orders-2026-09-29.jsonl`.
The log says all checks passed.

What the warehouses reported that morning:

- **Short picks.** The pick lists asked for stock that wasn't there: Leipzig 127 units short over 18 SKUs (e.g.
  HM-1128: the pick lists asked for 40, the bin held 7; GD-1059: 43 asked, 41 there), Rotterdam 82 units over
  19 SKUs (e.g. HM-1124: 46 asked, 34 there; HM-1063: 29 asked, 3 there), and Leeds 1 unit. Those orders went
  out late or partial.
- **Too many units packed.** 79 order lines on 77 orders were packed with more units than the customer ordered,
  335 units in total, mostly in Rotterdam (212), then Leipzig (107) and Madrid (16). For example:
  - M-882837 line 1: 1 × HM-1128 ordered, Rotterdam's pick list said 11;
  - M-881369 line 1: one 3-pack of LT-1055 (3 units) ordered, Rotterdam packed 7;
  - M-884970 line 1: 1 × HM-1064 ordered, Rotterdam packed 6.
  Packers caught some of these; the rest shipped.

The stock figures were right: Leipzig and Rotterdam counted the short SKUs that morning, and the counts matched what
the inventory service reported at 02:00 minus that night's picks.

Expected: a pick list never asks a warehouse for more than it has, a line is never allocated more units than were
ordered, and the allocation follows the policy in the README.

We can't re-run that night: the inventory service only knows current levels, and they've changed since (that
day's picking, two inbound deliveries, the counts). The OMS export is all we kept. Please fix the job so this can't
happen again.
