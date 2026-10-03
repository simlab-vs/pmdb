# September month-end: far too many points expired

The nightly points job ran as usual for the September month end (cron, 23:50 on Sep 30, on the loyalty box):

```
cd /srv/loyalty/nightly && python3 nightly.py --db /srv/loyalty/data/points.db --log logs/nightly-2026-09-30.log
```

Its log and reports are in `logs/` and `reports/`.

Since Oct 1, customer service has had a stream of complaints (31 so far) from members whose points expired at the
end of September although, according to them, they weren't due yet. A few members sent screenshots of the app showing
their points history, with lots marked "expired 30.09.2026".

The loyalty platform team checked the run against the terms and conditions. They restored the 23:45 backup (taken
just before the run) into a sandbox and computed with their audit SQL what the month end should have produced:

| Sep 30 month end | our report | audit |
|---|---|---|
| Expired points | 742,058 | 468,705 |
| ... purchase | 651,461 | 407,230 |
| ... promo | 86,793 | 59,071 |
| ... goodwill | 3,804 | 2,404 |
| Members with expiry | 1,136 | 902 |
| Forfeited (closed accounts) | 192,095 | 192,095 |
| Outstanding points | 16,071,024 | 16,344,377 |
| Liability (EUR, after breakage) | 65,891.20 | 67,011.95 |
| Expiring 2026-10-31 | 342,633 | 615,986 |

Posting of the day's activity (earn/burn/adjustments) matches the audit exactly, and so do the August month end and
the daily runs since.

We can't re-run the September month end: the database has moved on (the run itself booked the expiry and posted
September, and members have earned and redeemed since), the 23:45 backup has rotated out, and the sandbox was dropped
because it held members' personal data. The job's log and reports are all we have from that run.

We'll correct the affected members' balances by hand. Please fix the job so that the coming month ends expire exactly
what the terms and conditions say (for this run: the audit's figures).
