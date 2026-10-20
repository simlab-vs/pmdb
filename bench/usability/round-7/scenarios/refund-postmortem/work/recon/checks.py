"""Sanity checks run before the report is written.

Problems found here are logged; only structural ones stop the job.
"""

import logging

from .models import KINDS, OTHER

log = logging.getLogger(__name__)


class CheckFailed(RuntimeError):
    pass


def check_kinds(kinds):
    """Log how many events of each kind every provider sent."""
    for provider, counts in sorted(kinds.items()):
        log.info(
            "%s: %s",
            provider,
            ", ".join(f"{counts[kind]} {kind}" for kind in KINDS if counts[kind]),
        )
        if counts[OTHER] > 0.2 * sum(counts.values()):
            log.warning("%s: %d events of unknown types", provider, counts[OTHER])


def check_currencies(foreign, settlement_currency):
    """Log the transactions that needed an FX conversion."""
    if foreign:
        log.info(
            "converted %d transactions into %s (%s)",
            sum(foreign.values()),
            settlement_currency,
            ", ".join(f"{cur} {n}" for cur, n in sorted(foreign.items())),
        )


def check_refund_parents(earlier):
    """Log refunds and disputes of charges that are not in this period's export."""
    for provider, count in sorted(earlier.items()):
        log.info("%s: %d refunds or disputes of charges made before this period", provider, count)


def check_books(ledger):
    """Refuse to report a book that cannot be right."""
    for provider, book in ledger.books.items():
        if book.gross < 0 or book.fees < 0:
            raise CheckFailed(f"{provider}: negative gross volume or fees")
        if book.gross and book.refunds > book.gross:
            raise CheckFailed(f"{provider}: refunds exceed gross volume")
        if book.gross and book.fees > book.gross // 10:
            log.warning("%s: fees above 10%% of gross volume", provider)
