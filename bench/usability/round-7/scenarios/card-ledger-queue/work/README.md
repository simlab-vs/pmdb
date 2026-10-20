# cardledger

Daily ledger run of the Kite Prepaid EUR card programme (KPE-01).

The card processor sends a notification for every card event (authorizations, reversals, clearings, refunds,
top-ups) to the `card-events-prod` queue. Once a day, after the business date's traffic has drained, this job
drains the queue, posts the events to the card ledgers and writes the end-of-day files for the issuing bank.

Cron on the ledger box, 04:10 UTC:

```
cd /srv/cardledger && python3 run_ledger.py --business-date $(date -u -d yesterday +%F) --log logs/cardledger-$(date -u -d yesterday +%F).log
```

- **Input:** the queue, through the queue gateway (`config/settings.toml`). It is a standard queue: delivery is at
  least once and unordered. Messages are acknowledged (deleted) batch by batch as they are posted; nothing is kept
  after the run. Notification formats are documented in `ledger/messages.py`.
- **Offline runs:** `--spool DUMP` (or `CARDLEDGER_SPOOL=DUMP`) reads a queue dump instead of the queue: JSON Lines,
  optionally gzip-compressed, one received message per line in the order received, with the gateway's fields:

  ```
  {"MessageId": "…", "ReceiptHandle": "…", "Attributes": {"SentTimestamp": "1790640012000", "ApproximateReceiveCount": "1"},
   "Body": "{\"event_id\": \"evt_…\", \"type\": \"clearing\", \"created\": \"…\", \"programme\": \"KPE-01\", \"data\": {…}}"}
  ```
- **Output** (`reports/`):
  - `eod-balances-YYYY-MM-DD.csv`: per card, the day's net movement and the amount held at close. Sent to the
    issuing bank, which applies it to the card balances.
  - `settlement-YYYY-MM-DD.txt` / `.json`: totals per posting kind and merchant group. Finance reconciles them
    with the bank's daily settlement report.

Python 3.11+, no dependencies.
