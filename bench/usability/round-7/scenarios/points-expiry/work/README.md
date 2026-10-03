# loyalty-nightly

Nightly points job of Northwind Rewards (about 4,800 members in the pilot region).

Cron runs it every night at 23:50 Europe/Berlin on the loyalty box:

```
50 23 * * *  cd /srv/loyalty/nightly && python3 nightly.py --db /srv/loyalty/data/points.db --log logs/nightly-$(date +\%F).log
```

What it does:

- **Every night:** posts the day's pending earn/burn/adjust records (delivered by the POS and web-shop feeds into
  the `activity` table) to the members' points lots and the ledger.
- **On the last day of a month:** books the month's expiry (terms and conditions, section 7, see
  `loyalty/policy.py`) and the forfeiture of closed accounts, and pushes every open account's monthly statement to
  the CRM (one request per statement), which e-mails it and shows it in the app.
- Writes `reports/nightly-<date>.json` (imported by finance) and `.txt`; at month end also
  `reports/liability-<month>.txt` for the controller.

The points database is the live one (SQLite, `/srv/loyalty/data/points.db`), shared with the app back end and the
feeds. Backups: every night at 23:45, kept for 48 hours.

Configuration: `config/loyalty.toml`. Python 3.11+, no dependencies.
