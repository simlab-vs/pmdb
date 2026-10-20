# September billing run doesn't reconcile with MDM (77.7 kWh short)

The September billing cycle ran as usual on Oct 1 (cron on the billing box, 06:00):

```
cd /srv/billing/app && python3 run_billing.py --period 2026-09 --data /srv/billing/extract/2026-09 --out /srv/billing/out
```

Its summary and exceptions report are in `reports/`, and its log is in `logs/`. The run summary says:

```
  bills issued                   3,070
    on actual readings           2,966
    on estimates                   104
  metered consumption      1,941,062.2 kWh
```

Our meter data management system (MDM) reports **1,941,139.9 kWh** of validated consumption for the same accounts
and period, so billing is **77.7 kWh short**. Every previous month the two agreed exactly. The number of bills is
right (3,070 accounts were supplied in September), and the 104 estimated bills are exactly the accounts MDM lists as
missing a reading, so it isn't an account that dropped out or got estimated.

We can't see which account(s) are under-billed: none of the bills is in the exceptions report, and the bills have
already gone out to customers through the print house. Nothing changed on our side except that the September extract
is new.

I can't give you the extract. It holds the customer register and every customer's meter readings, and under our data
retention policy the billing box deletes it once the bills are issued; MDM only keeps validated totals, not the
operators' raw feeds. The summary, the exceptions report and the log above are all we have from that run.

Expected: the run's metered consumption matches MDM (1,941,139.9 kWh), with whichever bill(s) are wrong billed for
their full consumption.
