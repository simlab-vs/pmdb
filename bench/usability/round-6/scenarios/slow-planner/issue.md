# Overloaded truck in the plan for Monday 28 September

I ran the planner for Monday's deliveries as usual:

```
python3 plan_day.py data/orders_2026-09-28.json --fleet data/fleet.json -o out/
```

It takes about three minutes on my machine. The summary at the end says:

```
plan for 2026-09-28
stops: 1200
vehicles used: 90 (32 trucks, 58 vans)
distance: 4591.7 km
cost: 8542.68
utilisation: 97.9%
problems: 1
  capacity: T-44 carries 1614 kg, capacity 1600 kg
```

T-44 is one of our small trucks, rated 1,600 kg, so this route can't be driven as planned: the
dispatcher had to move two parcels to another truck by hand this morning. As far as I know the
planner should never put more on a vehicle than it can carry; it has always respected capacities
and windows before, and the input looks normal to me (orders and fleet are in `data/`).

Expected: a plan with no problems (no vehicle over its capacity), even if it costs a little more
or needs one more vehicle. Please fix the planner, not the data.
