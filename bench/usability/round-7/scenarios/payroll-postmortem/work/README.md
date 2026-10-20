# payroll

Monthly payroll for Brandt & Kessler Logistik GmbH (salaried and hourly staff, EUR).

Cron runs it on the last day of each month on the payroll box, after HR's export at 18:00:

```
cd /srv/payroll/app && python3 run_payroll.py --hr-export /srv/payroll/in/hr-YYYY-MM.json --period YYYY-MM --log logs/payroll-YYYY-MM.log
```

- Input: the HR system's export for the period (JSON; format in `payroll/hrexport.py`): persons with their
  assignment rows (contract terms with validity dates), absences, and the approved timesheets of hourly staff.
  It holds personal data: the wrapper script deletes it once the bank has acknowledged the transfer file
  (data-protection policy DP-7, retention 0 days on the payroll box).
- Rules: `config/payroll.toml` (allowances, premiums, contribution ceilings and rates, tax tariff, holidays).
- Output:
  - `reports/payroll-register-YYYY-MM.txt` (finance) and `.json` (GL import): totals per cost centre;
  - `/srv/payroll/out/credit-transfers-YYYY-MM.csv`: one transfer per payslip, sent to the bank by the wrapper.

Pay rules in short: salaries are prorated by calendar days of employment, hourly staff are paid from their
timesheets with night, Sunday/holiday and overtime premiums, a meal allowance is paid per working day, and
contributions and wage tax follow the (simplified) 2026 tables in the config. Each module's docstring has the
details. Python 3.11+, no dependencies.
