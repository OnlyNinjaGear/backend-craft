# SQLAlchemy context: every text() here resolves to sqlalchemy.text -> must fire.
from sqlalchemy import text
import sqlalchemy as sa


def probes(conn, x, table, value):
    # ruleid: backend-craft.python.sql-text-fstring
    conn.execute(text(f"SELECT {x}"))
    # ruleid: backend-craft.python.sql-text-format-or-concat
    conn.execute(text("SELECT %s" % x))
    # ruleid: backend-craft.python.sql-text-format-or-concat
    conn.execute(text("SELECT {}".format(x)))
    # ruleid: backend-craft.python.sql-text-format-or-concat
    conn.execute(text("SELECT " + table))
    # ruleid: backend-craft.python.sql-text-fstring
    conn.execute(sa.text(f"SELECT {x}"))
    # ruleid: backend-craft.python.sql-text-format-or-concat
    sa.text("SELECT " + table)
    # ok: backend-craft.python.sql-text-fstring
    conn.execute(text("SELECT 1"))
    # ok: backend-craft.python.sql-text-format-or-concat
    conn.execute(text("SELECT id FROM t WHERE id = :id"), {"id": value})
