"""The customer register: accounts, their tariffs and identifiers."""

import csv
import logging
import re
from typing import NamedTuple

from . import periods

log = logging.getLogger(__name__)

_ID_PATTERN = re.compile(r"([A-Z]{2})-?(\d{1,6})")


class UnknownAccount(KeyError):
    """Raised when an identifier matches no account of the register."""


class Account(NamedTuple):
    account: str
    name: str
    segment: str
    tariff: str
    eac: float
    move_in: str
    move_out: str
    legacy_id: str


def canonical_id(raw):
    """Normalize an account identifier as typed by people and vendors.

    ``" ac4127"``, ``"AC-4127"`` and ``"AC-004127"`` all become
    ``"AC-004127"``.  Identifiers of another shape are only stripped and
    upper-cased.
    """
    text = raw.strip().upper()
    match = _ID_PATTERN.fullmatch(text)
    if match is None:
        return text
    prefix, number = match.groups()
    return f"{prefix}-{int(number):06d}"


class Register:
    """Accounts by identifier.

    Accounts taken over from Northwind Energy in 2024 keep their Northwind
    number as ``legacy_id``; some meter operators still report under it.
    """

    def __init__(self, accounts):
        self._accounts = {}
        self._aliases = {}
        for account in accounts:
            if account.account in self._accounts:
                raise ValueError(f"duplicate account {account.account}")
            self._accounts[account.account] = account
            if account.legacy_id:
                self._aliases[canonical_id(account.legacy_id)] = account.account

    def __len__(self):
        return len(self._accounts)

    def __contains__(self, account_id):
        return account_id in self._accounts

    def resolve(self, raw):
        """The register's identifier for ``raw`` (current or legacy)."""
        key = canonical_id(raw)
        if key in self._accounts:
            return key
        try:
            return self._aliases[key]
        except KeyError:
            raise UnknownAccount(raw) from None

    def get(self, account_id):
        return self._accounts[account_id]

    def accounts(self):
        """Accounts by register identifier."""
        return dict(self._accounts)

    def identifiers(self):
        """Every known identifier (canonical form) mapped to the register's."""
        table = {account_id: account_id for account_id in self._accounts}
        for legacy, account_id in self._aliases.items():
            table.setdefault(legacy, account_id)
        return table

    def active(self, period):
        """Accounts supplied for at least one day of ``period``."""
        return [
            account
            for account in self._accounts.values()
            if periods.overlap_days(period, account.move_in, account.move_out) > 0
        ]


def _parse_account(row):
    return Account(
        account=canonical_id(row["account"]),
        name=row["name"].strip(),
        segment=row["segment"].strip().lower(),
        tariff=row["tariff"].strip().upper(),
        eac=float(row["eac_kwh"] or 0),
        move_in=row["move_in"].strip(),
        move_out=row["move_out"].strip(),
        legacy_id=row["legacy_id"].strip(),
    )


def load_register(path):
    """Read ``customers.csv``."""
    with open(path, newline="", encoding="utf-8") as handle:
        accounts = [_parse_account(row) for row in csv.DictReader(handle)]
    register = Register(accounts)
    legacy = sum(1 for account in accounts if account.legacy_id)
    log.info("register: %d accounts (%d with a legacy number)", len(register), legacy)
    return register
