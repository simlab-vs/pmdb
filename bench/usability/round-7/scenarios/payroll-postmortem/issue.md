# September payroll: salaries €16,904.43 higher than HR's payroll preview

The September payroll ran as usual on Sep 30 (cron on the payroll box, 22:30):

```
cd /srv/payroll/app && python3 run_payroll.py --hr-export /srv/payroll/in/hr-2026-09.json --period 2026-09 --log logs/payroll-2026-09.log
```

The register it wrote and its log are in `reports/` and `logs/`. The transfers went out on Oct 1.

During the month-end close, HR compared our register with the payroll preview their HR system calculates from the
same data. Hourly pay and premiums agree to the cent, and so does the headcount (619). Base salaries and meal
allowances don't:

| September 2026 | our register | HR preview | difference |
|---|---|---|---|
| Base salaries | 2,163,813.44 | 2,146,909.01 | +16,904.43 |
| Hourly pay | 637,033.10 | 637,033.10 | 0.00 |
| Premiums | 65,119.99 | 65,119.99 | 0.00 |
| Meal allowances | 94,747.50 | 94,245.00 | +502.50 |
| **Gross** | **2,960,714.03** | **2,943,307.10** | +17,406.93 |
| Employee contributions | 556,198.00 | 552,863.24 | +3,334.76 |
| Wage tax | 388,516.96 | 384,599.28 | +3,917.68 |
| **Net (paid out)** | **2,015,999.07** | **2,005,844.58** | +10,154.49 |
| Employer contributions | 543,585.25 | 540,324.95 | +3,260.30 |

Base salaries per cost centre:

| cost centre | our register | HR preview |
|---|---|---|
| CC-110 Administration | 357,565.26 | 357,565.26 |
| CC-120 Finance & HR | 425,361.53 | 417,774.87 |
| CC-210 Warehouse Nord | 217,681.36 | 216,135.36 |
| CC-220 Warehouse Süd | 269,074.00 | 265,164.73 |
| CC-310 Transport | 192,453.20 | 189,724.17 |
| CC-410 Sales | 366,235.63 | 366,235.63 |
| CC-510 IT | 335,442.46 | 334,308.99 |

HR's preview is what the contracts say; we've used it for years as the four-eyes check and it has always matched
until now (August was fine). We overpaid about €10k net, and the tax and contribution filings for September are
due on the 10th.

The HR export can't be given to you: it holds personal data and was deleted from the payroll box after the bank
acknowledged the transfers, as our data-protection policy requires, and it may not leave the payroll box anyway.
The register, the log and the code are what we have. Please find out why we paid more and fix the job so that
it matches HR's preview: we'll re-run September in production on a fresh export for the correction payslips,
and October's payroll must come out right.
