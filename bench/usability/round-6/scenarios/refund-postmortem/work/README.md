# payout-recon

Monthly payout reconciliation for our card-payment providers (Kestrel, Lumen, NovaPay).

Cron runs it on the first of each month on the recon box:

```
cd /srv/payout-recon && python3 monthly_report.py --export /srv/exports/events-YYYY-MM.jsonl.gz --month YYYY-MM --log logs/payout-recon-YYYY-MM.log
```

- Input: the gateway's webhook archive for the month (JSON Lines, gzip), one provider event per line, with a
  `provider` field. The archive includes a few hours of the neighbouring months and may contain redeliveries.
- FX: `config/fx/YYYY-MM.csv`, daily reference rates (units of currency per EUR), used for Lumen's
  non-EUR payments.
- Output: `reports/payout-recon-YYYY-MM.txt` for finance and `.json` for the ledger import. Finance checks the
  per-provider net against each provider's settlement statement.

Provider event formats are documented in `recon/providers/`. Python 3.11+, no dependencies.
