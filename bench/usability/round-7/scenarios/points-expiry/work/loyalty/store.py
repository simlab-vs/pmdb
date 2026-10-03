"""Access to the points database (SQLite).

Tables:

- ``members``: one row per member (tier, status, marketing opt-in);
- ``lots``: points earned together, with what is left of them (``remaining``)
  and, once expired or forfeited, the business date it happened (``closed_on``);
- ``activity``: earn/burn/adjust records delivered by the POS and web-shop
  feeds, ``pending`` until the nightly job posts them;
- ``ledger``: every booked movement of points;
- ``job_runs``: one row per run of the nightly job.
"""

import contextlib
import logging
import sqlite3

from .models import Activity, Lot, Member

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY, tier TEXT NOT NULL, status TEXT NOT NULL,
    joined_on TEXT NOT NULL, opt_in INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, earned_on TEXT NOT NULL,
    source TEXT NOT NULL, points INTEGER NOT NULL, remaining INTEGER NOT NULL,
    closed_on TEXT
);
CREATE INDEX IF NOT EXISTS lots_member ON lots (member_id, remaining);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, business_date TEXT NOT NULL,
    kind TEXT NOT NULL, source TEXT NOT NULL, points INTEGER NOT NULL,
    ref TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', posted_at TEXT
);
CREATE INDEX IF NOT EXISTS activity_day ON activity (business_date, status);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY, member_id TEXT NOT NULL, posted_on TEXT NOT NULL,
    kind TEXT NOT NULL, points INTEGER NOT NULL, lot_id INTEGER, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ledger_member ON ledger (member_id, posted_on);
CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY, business_date TEXT NOT NULL, started_at TEXT NOT NULL,
    finished_at TEXT, mode TEXT NOT NULL, status TEXT NOT NULL, summary TEXT
);
"""


class StoreError(RuntimeError):
    pass


def connect(path):
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@contextlib.contextmanager
def transaction(conn):
    conn.execute("BEGIN")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


MEMBER_COLUMNS = "id, tier, status, joined_on, opt_in"
LOT_COLUMNS = "id, member_id, earned_on, source, points, remaining"


def all_members(conn):
    rows = conn.execute(f"SELECT {MEMBER_COLUMNS} FROM members ORDER BY id").fetchall()
    return [Member(row[0], row[1], row[2], row[3], bool(row[4])) for row in rows]


def member_count(conn):
    return conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]


def open_lots(conn, member_id):
    rows = conn.execute(
        f"SELECT {LOT_COLUMNS} FROM lots WHERE member_id = ? AND remaining > 0 ORDER BY earned_on, id",
        (member_id,),
    ).fetchall()
    return [Lot._make(row) for row in rows]


def open_lots_of(conn, member_ids):
    """Open lots of several members, by member id, each in earning order."""
    result = {member_id: [] for member_id in member_ids}
    marks = ",".join("?" * len(member_ids))
    rows = conn.execute(
        f"SELECT {LOT_COLUMNS} FROM lots WHERE remaining > 0 AND member_id IN ({marks}) "
        f"ORDER BY member_id, earned_on, id",
        list(member_ids),
    ).fetchall()
    for row in rows:
        result[row["member_id"]].append(Lot._make(row))
    return result


def pending_activity(conn, business_date):
    rows = conn.execute(
        "SELECT * FROM activity WHERE business_date = ? AND status = 'pending' ORDER BY id", (business_date,)
    ).fetchall()
    for row in rows:
        yield Activity(row["id"], row["member_id"], row["business_date"], row["kind"], row["source"],
                       row["points"], row["ref"])


def pending_count(conn, business_date):
    return conn.execute(
        "SELECT COUNT(*) FROM activity WHERE business_date = ? AND status = 'pending'", (business_date,)
    ).fetchone()[0]


def later_pending_count(conn, business_date):
    return conn.execute(
        "SELECT COUNT(*) FROM activity WHERE business_date > ? AND status = 'pending'", (business_date,)
    ).fetchone()[0]


def mark_posted(conn, activity_id, posted_at):
    conn.execute("UPDATE activity SET status = 'posted', posted_at = ? WHERE id = ?", (posted_at, activity_id))


def mark_rejected(conn, activity_id, posted_at):
    conn.execute("UPDATE activity SET status = 'rejected', posted_at = ? WHERE id = ?", (posted_at, activity_id))


def insert_lot(conn, member_id, earned_on, source, points):
    cursor = conn.execute(
        "INSERT INTO lots (member_id, earned_on, source, points, remaining) VALUES (?, ?, ?, ?, ?)",
        (member_id, earned_on, source, points, points),
    )
    return cursor.lastrowid


def take_from_lot(conn, lot_id, points):
    cursor = conn.execute(
        "UPDATE lots SET remaining = remaining - ? WHERE id = ? AND remaining >= ?", (points, lot_id, points)
    )
    if cursor.rowcount != 1:
        raise StoreError(f"lot {lot_id} has fewer than {points} points left")


def close_lot(conn, lot_id, closed_on):
    conn.execute("UPDATE lots SET remaining = 0, closed_on = ? WHERE id = ?", (closed_on, lot_id))


def insert_ledger(conn, member_id, posted_on, kind, points, lot_id, created_at):
    conn.execute(
        "INSERT INTO ledger (member_id, posted_on, kind, points, lot_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, posted_on, kind, points, lot_id, created_at),
    )


def month_movements(conn, member_ids, first_day, last_day):
    """Ledger totals per member and kind for the days ``first_day .. last_day``."""
    result = {member_id: {} for member_id in member_ids}
    marks = ",".join("?" * len(member_ids))
    rows = conn.execute(
        f"SELECT member_id, kind, SUM(points) AS points FROM ledger "
        f"WHERE posted_on BETWEEN ? AND ? AND member_id IN ({marks}) GROUP BY member_id, kind",
        [first_day, last_day, *member_ids],
    ).fetchall()
    for row in rows:
        result[row["member_id"]][row["kind"]] = row["points"]
    return result


def ledger_total(conn, posted_on, kind):
    row = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM ledger WHERE posted_on = ? AND kind = ?", (posted_on, kind)
    ).fetchone()
    return row[0]


def open_points_by_member(conn):
    rows = conn.execute(
        "SELECT m.id, m.tier, m.status, COALESCE(SUM(l.remaining), 0) AS points "
        "FROM members m LEFT JOIN lots l ON l.member_id = m.id AND l.remaining > 0 GROUP BY m.id ORDER BY m.id"
    ).fetchall()
    return [(row["id"], row["tier"], row["status"], row["points"]) for row in rows]


def open_points_by_earning(conn):
    """Open points by member tier and status, lot source and earning date (for the liability report)."""
    rows = conn.execute(
        "SELECT m.tier, m.status, l.source, l.earned_on, SUM(l.remaining) FROM lots l "
        "JOIN members m ON m.id = l.member_id WHERE l.remaining > 0 "
        "GROUP BY m.tier, m.status, l.source, l.earned_on ORDER BY 1, 2, 3, 4"
    ).fetchall()
    return [tuple(row) for row in rows]


def lot_violations(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM lots WHERE remaining < 0 OR remaining > points"
    ).fetchone()[0]


def start_run(conn, business_date, started_at, mode):
    cursor = conn.execute(
        "INSERT INTO job_runs (business_date, started_at, mode, status) VALUES (?, ?, ?, 'running')",
        (business_date, started_at, mode),
    )
    return cursor.lastrowid


def finish_run(conn, run_id, finished_at, status, summary):
    conn.execute(
        "UPDATE job_runs SET finished_at = ?, status = ?, summary = ? WHERE id = ?",
        (finished_at, status, summary, run_id),
    )


def previous_run(conn, business_date):
    row = conn.execute(
        "SELECT * FROM job_runs WHERE business_date = ? AND status = 'ok' ORDER BY id DESC LIMIT 1",
        (business_date,),
    ).fetchone()
    return dict(row) if row else None
