"""SQLite persistence: load the migration, seed two orgs, hand out one shared
in-memory connection. Raw stdlib sqlite3 — no ORM.
"""
import sqlite3
from pathlib import Path

MIGRATION = Path(__file__).resolve().parent.parent / "migrations" / "001_init.sql"

_conn: sqlite3.Connection | None = None


def _build() -> sqlite3.Connection:
    # isolation_level=None -> autocommit; we manage explicit BEGIN/COMMIT where
    # we want a real transaction. check_same_thread=False so the TestClient
    # worker thread can share the single in-memory database.
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(MIGRATION.read_text())
    _seed(conn)
    return conn


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO orgs (id, name) VALUES (?, ?)",
        [(1, "Acme"), (2, "Globex")],
    )
    conn.executemany(
        "INSERT INTO users (id, org_id, email, name, role) VALUES (?, ?, ?, ?, ?)",
        [
            (1, 1, "alice@acme.test", "Alice", "admin"),
            (2, 2, "bob@globex.test", "Bob", "member"),
        ],
    )
    conn.executemany(
        "INSERT INTO projects (id, org_id, name, status) VALUES (?, ?, ?, ?)",
        [
            (1, 1, "Acme Website", "active"),
            (2, 1, "Acme Mobile App", "active"),
            (3, 2, "Globex Platform", "active"),
        ],
    )
    conn.executemany(
        "INSERT INTO invoices (id, org_id, project_id, amount_cents, status) VALUES (?, ?, ?, ?, ?)",
        [
            (1, 1, 1, 5000, "unpaid"),
            (2, 1, 2, 12000, "unpaid"),
            (3, 2, 3, 9000, "unpaid"),
        ],
    )


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _build()
    return _conn


def reset_db() -> sqlite3.Connection:
    """Rebuild the seeded database (used by tests for isolation)."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None
    return get_conn()
