# September billing run doesn't reconcile with MDM (77.7 kWh short)

We ran the September billing cycle as usual:

```
python3 run_billing.py --period 2026-09 --data data --out out
```

(`data/` is the September extract: customer register, tariffs, meter events and the three
operators' reading feeds; it's in the repo.)

The run summary says:

```
  bills issued                   3,070
    on actual readings           2,966
    on estimates                   104
  metered consumption      1,941,062.2 kWh
```

Our meter data management system (MDM) reports **1,941,139.9 kWh** of validated consumption
for the same accounts and period, so billing is **77.7 kWh short**. Every previous month the
two agreed exactly. The number of bills is right (3,070 accounts were supplied in September), and
the 104 estimated bills are exactly the accounts MDM lists as missing a reading, so it isn't an
account that dropped out or got estimated.

We can't see which account(s) are under-billed: none of the bills is in the exceptions report,
and we can't check 3,000 bills by hand. Nothing changed on our side except that the September
extract is new.

Expected: the run's metered consumption matches MDM (1,941,139.9 kWh), with whichever bill(s)
are wrong billed for their full consumption.
