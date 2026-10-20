# Card ledger for Sep 28: clearings €808.30 below the bank's settlement

The ledger run for business date 2026-09-28 ran as usual from cron on the ledger box, on Sep 29 at 04:10 UTC:

```
cd /srv/cardledger && python3 run_ledger.py --business-date 2026-09-28 --log logs/cardledger-2026-09-28.log
```

Its log and settlement summary are in `logs/` and `reports/`. No warnings, no errors.

Finance reconciled the summary with Hallbank's daily settlement report for KPE-01 on Sep 30, and it doesn't agree:

| 2026-09-28 | our settlement summary | Hallbank settlement |
|---|---|---|
| Clearings (presentments) | 306,793.51 | 307,601.81 |
| Refunds | 6,140.28 | 6,140.28 |
| Top-ups | 81,991.11 | 81,991.11 |
| **Net card movement** (incl. our fees 697.92 FX, 22.50 ATM) | **-219,382.54** | **-220,190.84** |

So we posted €808.30 less in clearings than the bank settled with the scheme, and the end-of-day balance file we
sent overstates the card balances by the same amount. Hallbank's exception report says the movement differs on 202
cards, and every difference is a debit missing on our side. The bank's settlement is what was actually paid to the
acquirers, so it is right; the bank has corrected the balances manually for now.

We can't re-run the day. The job acknowledges and deletes the queue messages as it posts them, so they are gone,
and the processor only re-sends notifications within six hours. The log and the summary are all we have from that
run.

Please find out why the ledger missed these clearings and fix the job, so that it posts what the bank settles on the
coming days.
