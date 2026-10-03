# order-allocation

Nightly allocation of open order lines to our warehouses (Leeds, Rotterdam, Leipzig, Madrid).

Cron runs it at 02:00 (Europe/Amsterdam) on the allocation box, after the OMS export:

```
cd /srv/allocation && python3 allocate_night.py --orders /srv/oms/exports/open-lines-YYYY-MM-DD.jsonl --date YYYY-MM-DD --log logs/allocation-YYYY-MM-DD.log
```

- **Orders:** the OMS export of every order with open lines (JSON Lines, format in `alloc/orders.py`). Webshop
  (`W-`), marketplace (`M-`) and B2B (`B-`) orders.
- **Stock:** read at the start of the run from the inventory service (`[inventory] url` in
  `config/settings.toml`). The service only knows current levels. For offline runs and tests, pass a dump
  instead: `--levels-file levels.json` (format in `alloc/inventory.py`; `inventory-cli dump --all` writes one).
- **Policy:** lines are served first come, first served (express orders first). Each destination country has a
  sequence of warehouses (`[routing]`); a line takes what it can from each in turn and the rest is backordered.
  B2B ship-complete orders and kits ship from a single warehouse. Marketplace lines can't take a warehouse's
  safety stock, which is kept for our shop and B2B customers.
- **Output:** one pick list per warehouse in `out/` (picked up by the WMS at 02:15), and the allocation summary
  `reports/allocation-YYYY-MM-DD.txt` / `.json` (the JSON is imported by the OMS: backorders).
- **Master data:** `catalog/skus.csv` (handling attributes) and `catalog/kits.csv` (kit components).

Python 3.11+, no dependencies.
