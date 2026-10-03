"""Booking normalized transactions into one book per provider."""

import itertools
import logging
from collections import Counter

from .models import CHARGE, REFUND, DISPUTE, OTHER

log = logging.getLogger(__name__)


class Book:
    """Settlement totals of one provider, in settlement minor units."""

    def __init__(self, provider):
        self.entry_numbers = itertools.count(1)
        self.entries = 0
        self.provider = provider
        self.gross = 0
        self.fees = 0
        self.refunds = 0
        self.disputes = 0
        self.counts = Counter()
        self.skipped = Counter()

    @property
    def net(self):
        return self.gross - self.fees - self.refunds - self.disputes

    def totals(self):
        return {
            "gross": self.gross,
            "fees": self.fees,
            "refunds": self.refunds,
            "disputes": self.disputes,
            "net": self.net,
        }


class Ledger:
    def __init__(self, providers, ignored_statuses):
        self.books = {provider: Book(provider) for provider in providers}
        self.ignored_statuses = frozenset(ignored_statuses)

    def book(self, provider):
        return self.books[provider]

    def apply(self, txn):
        """Book one transaction; returns False if it was not booked."""
        book = self.books[txn.provider]
        if txn.status in self.ignored_statuses:
            book.skipped[txn.status] += 1
            return False
        if txn.kind == CHARGE:
            self.apply_charge(book, txn)
        elif txn.kind == REFUND:
            self.apply_refund(book, txn)
        elif txn.kind == DISPUTE:
            self.apply_dispute(book, txn)
        else:
            book.counts[OTHER] += 1
            return False
        book.counts[txn.kind] += 1
        book.entries = next(book.entry_numbers)
        return True

    def apply_charge(self, book, txn):
        book.gross += txn.settle_amount
        book.fees += txn.fee

    def apply_refund(self, book, txn):
        book.refunds += txn.settle_amount
        book.fees += txn.fee

    def apply_dispute(self, book, txn):
        book.disputes += txn.settle_amount
        book.fees += txn.fee

    def log_summary(self):
        for provider, book in self.books.items():
            log.info(
                "%s: booked %d entries (%d charges, %d refunds, %d disputes); skipped %s",
                provider,
                book.entries,
                book.counts[CHARGE],
                book.counts[REFUND],
                book.counts[DISPUTE],
                ", ".join(f"{n} {status}" for status, n in sorted(book.skipped.items())) or "none",
            )
