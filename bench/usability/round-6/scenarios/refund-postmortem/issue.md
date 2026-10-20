# September payout reconciliation: NovaPay net is €5,027.67 below NovaPay's settlement statement

The monthly reconciliation job ran as usual on Oct 1 (cron on the recon box):

```
cd /srv/payout-recon && python3 monthly_report.py --export /srv/exports/events-2026-09.jsonl.gz --month 2026-09 --log logs/payout-recon-2026-09.log
```

The report it wrote and its log are in `reports/` and `logs/`.

Kestrel and Lumen agree with their September settlement statements to the cent. NovaPay doesn't. Our report says:

| NovaPay, Sep 2026 | our report | NovaPay statement |
|---|---|---|
| Charges (gross) | 350,695.74 | 350,695.74 |
| Fees | 6,464.68 | 6,464.68 |
| Refunds | 16,966.45 | 11,938.78 |
| Disputes | 624.36 | 624.36 |
| **Net settlement** | **326,640.25** | **331,667.92** |

So our refunds are €5,027.67 too high, and the net and the totals line are too low by the same amount. NovaPay's
statement is what they actually paid out, and their support says the figures are final. August reconciled fine.

I can't give you the export: it holds customer payment data and doesn't leave the prod box. The job's output and
log from that run are all we have. Finance needs the job to produce NovaPay's numbers (refunds 11,938.78, net
331,667.92, so a total net of 1,028,584.40) when it's re-run on the September export, and to get the coming months
right.
