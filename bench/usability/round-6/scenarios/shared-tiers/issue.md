# September invoices: API requests undercharged on some Scale invoices

I ran the September invoicing as usual:

```
python3 run_invoices.py data --period 2026-09 --out out
```

While spot-checking invoices against the price sheet (`data/plans.json`) before sending them
out, I found Scale plan invoices whose "API requests" line is far too low. The other lines (base
fee, storage, data transfer, seats) are correct on all of them.

| Invoice | Customer | API requests | Billed | Should be |
|---|---|---|---|---|
| INV-2026-09-1047 | C11055 Onyx Onyx Analytics | 7,806,714 | 2,192.01 EUR | 4,384.03 EUR |
| INV-2026-09-1089 | C11097 Ember Echo Ltd | 19,534,819 | 5,710.45 EUR | 8,565.67 EUR |
| INV-2026-09-1102 | C11110 Kestrel Granite SAS | 6,945,470 | 1,669.50 GBP | 3,339.01 GBP |

"Should be" is what I get by hand: Scale's API requests are volume priced with 500,000
included, so for INV-2026-09-1047 that's 7,306,714 billable requests, in the 2M–10M tier at
0.0006 EUR = 4,384.03 EUR. The amounts billed look like every request was charged at 0.0003,
the rate for over 50M requests, which none of these customers come close to.

Most of the Scale invoices I checked are fine (e.g. INV-2026-09-0263, 2,842,305 requests,
1,405.38 EUR, correct), so it's not the whole plan. I haven't checked every invoice, so there may
be more. Nothing changed in the price sheet this month as far as I know.

Expected: API requests on every invoice charged at the tier rate from the price sheet.
