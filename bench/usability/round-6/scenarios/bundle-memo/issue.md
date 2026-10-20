# Two quotes from the 30 September run are higher than the shop price

Two customers wrote to customer service because the quote they got from Tuesday's run is higher
than what the shop shows for exactly the same basket (we checked the baskets in the shop admin,
same day, same customer account, same channel):

| Quote | Customer | Quote total | Shop total |
|---|---|---|---|
| Q-30260 | C-1309 (Jan Klein, Leipzig, member, picked up in store) | 72.59 | 72.11 |
| Q-30457 | C-1054 (Jan Becker, Gent, web) | 55.78 | 54.57 |

Both baskets got the loose tea 3-for-2, and the list price on the quote is right, but the subtotal
after offers is higher than the shop's. We spot-checked about twenty other quotes from the same
run and they all match the shop. The shop's pricing is the reference here; the prices and offers in
`data/` are the ones the shop uses, so please don't change the data.

The run was:

```
python3 quote_run.py data --date 2026-09-30 --out out
```

`out/quotes.csv` and `out/summary.txt` are the run's output. Can you find out why these quotes come
out wrong and fix it, so the run quotes what the shop charges?
