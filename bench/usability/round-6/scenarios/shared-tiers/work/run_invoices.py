"""Run the monthly invoicing: python3 run_invoices.py DATA --period YYYY-MM --out DIR"""

import sys

from invoicing.run import main

if __name__ == "__main__":
    sys.exit(main())
