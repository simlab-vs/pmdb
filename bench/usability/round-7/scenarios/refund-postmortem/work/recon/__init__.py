"""Monthly payout reconciliation for card-payment providers.

The job reads a month's export of provider events, normalizes them into
settlement-currency transactions, books them into one ledger per provider and
writes the reconciliation report that finance compares with the providers'
settlement statements.
"""

__version__ = "3.4.1"
