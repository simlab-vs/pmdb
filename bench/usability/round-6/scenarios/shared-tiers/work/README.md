# Cloudlane invoicing

Computes the monthly invoices of Cloudlane's customers from the metering export.

```
python3 run_invoices.py data --period 2026-09 --out out
```

## Inputs (`data/`)

| File | Content |
|---|---|
| `settings.json` | seller country, base currency, VAT rates, minimum invoice |
| `plans.json` | the price sheet: plans, their base fees and metered dimensions |
| `customers.csv` | billable customers, their plan, currency and negotiated discount |
| `contracts.json` | enterprise contracts with a committed monthly volume |
| `plan_changes.csv` | plan changes, effective from the given day |
| `fx.json` | monthly exchange rates from EUR |
| `usage_YYYY-MM.csv` | daily usage records exported by the metering service |

## Pricing

Every metric of a plan has a number of units included in the base fee, and a list of
price tiers for the units beyond it:

- `graduated`: each unit is charged at the price of the tier it falls in;
- `volume`: all units are charged at the price of the tier the total falls in;
- `per_unit`: a single price.

Invoices are in EUR, converted to the customer's currency line by line at the period's
rate. Base fees are prorated by day when a customer changes plan during the period.

## Outputs (`--out`)

- `invoices.jsonl`: one invoice per line;
- `invoice_lines.csv`: every invoice line, for the accounting import;
- `summary.txt`: invoice count, totals per currency and net revenue per plan.
