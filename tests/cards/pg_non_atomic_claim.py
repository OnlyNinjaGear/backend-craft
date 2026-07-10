"""Reducer for pg-non-atomic-poll-queue-claim (needs a reachable PostgreSQL).

Proves four separate facts about claiming jobs from a SQL table used as a queue.
The point of the card is NOT "you must use SKIP LOCKED"; it is "the claim must be
atomic, and even an atomic claim does not give exactly-once under a crash".

  1. NON-ATOMIC claim double-delivers. A plain `SELECT ... WHERE status='pending'`
     in one statement and a separate `UPDATE ... SET status='running'` in another,
     with no row lock and no status guard, hands the SAME row to two workers.

  2. `FOR UPDATE SKIP LOCKED` is a correct standard option: each pending row goes
     to exactly one worker and workers do not block on each other.

  3. A single conditional `UPDATE ... WHERE id=$1 AND status='pending' RETURNING id`
     is ALSO correct: under real concurrency the second writer blocks, re-checks the
     guard after the first commits, and claims zero rows. Exactly one worker wins.

  4. No claim strategy gives exactly-once. After an atomic claim, a worker can crash
     before finishing; a reaper requeues the stale row and it is delivered again.
     The consumer must be idempotent / dedupe / compensate.

Connection uses standard libpq env vars (PGHOST/PGUSER/PGDATABASE/PGPASSWORD...).
Run:
  PGHOST=/var/run/postgresql PGUSER=postgres PGDATABASE=bcdemo \
    uv run --with psycopg2-binary python tests/cards/pg_non_atomic_claim.py
"""
import os
import threading

import psycopg2

TABLE = "bc_claim_demo"


def connect():
    # psycopg2 reads standard PG* env vars when the argument is omitted/empty.
    return psycopg2.connect(os.environ.get("BC_PG_DSN", ""))


def reset(n_pending=1):
    """Fresh table with n_pending 'pending' rows (ids 1..n)."""
    conn = connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
        cur.execute(
            f"""CREATE TABLE {TABLE} (
                    id         int PRIMARY KEY,
                    status     text NOT NULL DEFAULT 'pending',
                    worker     text,
                    claimed_at timestamptz
                )"""
        )
        for i in range(1, n_pending + 1):
            cur.execute(f"INSERT INTO {TABLE} (id, status) VALUES (%s, 'pending')", (i,))
    conn.close()


# ---- Fact 1: non-atomic SELECT-then-UPDATE double-claims -------------------
def non_atomic_double_claim() -> dict:
    reset(1)
    a, b = connect(), connect()
    a.autocommit = True
    b.autocommit = True
    with a.cursor() as ca, b.cursor() as cb:
        ca.execute(f"SELECT id FROM {TABLE} WHERE status='pending' LIMIT 1")
        a_id = ca.fetchone()[0]
        # B polls before A has written anything back -> sees the same row.
        cb.execute(f"SELECT id FROM {TABLE} WHERE status='pending' LIMIT 1")
        b_id = cb.fetchone()[0]
        # Neither UPDATE guards on status, so both "succeed".
        ca.execute(f"UPDATE {TABLE} SET status='running', worker='A' WHERE id=%s", (a_id,))
        a_claimed = ca.rowcount
        cb.execute(f"UPDATE {TABLE} SET status='running', worker='B' WHERE id=%s", (b_id,))
        b_claimed = cb.rowcount
    a.close(); b.close()
    return {"a_id": a_id, "b_id": b_id, "a_claimed": a_claimed, "b_claimed": b_claimed}


# ---- Fact 2: FOR UPDATE SKIP LOCKED -> disjoint rows, no blocking ----------
def skip_locked_disjoint() -> dict:
    reset(2)
    a, b = connect(), connect()
    a.autocommit = False
    b.autocommit = False
    q = (f"SELECT id FROM {TABLE} WHERE status='pending' "
         f"ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1")
    with a.cursor() as ca, b.cursor() as cb:
        ca.execute(q)
        a_id = ca.fetchone()[0]          # locks row 1, tx still open
        cb.execute(q)                    # row 1 is locked -> skipped
        b_id = cb.fetchone()[0]          # gets row 2, did not block
    a.rollback(); b.rollback()
    a.close(); b.close()
    return {"a_id": a_id, "b_id": b_id}


# ---- Fact 3: conditional UPDATE ... RETURNING claims exactly once -----------
def conditional_update_exactly_once() -> dict:
    reset(1)
    upd = (f"UPDATE {TABLE} SET status='running', worker=%s "
           f"WHERE id=1 AND status='pending' RETURNING id")
    a = connect(); a.autocommit = False
    got = {}
    with a.cursor() as ca:
        ca.execute(upd, ("A",))
        got["a"] = ca.fetchall()          # [(1,)]; row lock held, NOT committed

    def worker_b():
        b = connect(); b.autocommit = False
        with b.cursor() as cb:
            cb.execute(upd, ("B",))        # blocks on A's row lock
            got["b"] = cb.fetchall()       # after A commits: guard fails -> []
        b.commit(); b.close()

    t = threading.Thread(target=worker_b)
    t.start()
    # give B time to reach the lock wait, then let A win.
    import time
    time.sleep(0.3)
    a.commit(); a.close()
    t.join(timeout=5)
    return {"a": got.get("a"), "b": got.get("b")}


# ---- Fact 4: crash after claim -> reaper requeues -> redelivered ------------
def crash_then_redelivery() -> dict:
    reset(1)
    claim = (f"UPDATE {TABLE} SET status='running', worker=%s, claimed_at=now() "
             f"WHERE id=1 AND status='pending' RETURNING id")
    deliveries = []
    # Worker A claims atomically, then "crashes" (never marks done).
    a = connect(); a.autocommit = True
    with a.cursor() as ca:
        ca.execute(claim, ("A",))
        if ca.fetchall():
            deliveries.append("A")
    a.close()
    # Reaper requeues rows stuck in 'running' (visibility timeout expired).
    r = connect(); r.autocommit = True
    with r.cursor() as cr:
        cr.execute(f"UPDATE {TABLE} SET status='pending', worker=NULL "
                   f"WHERE status='running' AND claimed_at < now()")
    r.close()
    # Worker B now claims the very same job -> second delivery.
    b = connect(); b.autocommit = True
    with b.cursor() as cb:
        cb.execute(claim, ("B",))
        if cb.fetchall():
            deliveries.append("B")
    b.close()
    return {"deliveries": deliveries}


def main():
    f1 = non_atomic_double_claim()
    print(f"1 non-atomic:   A claimed id={f1['a_id']} (rows={f1['a_claimed']}), "
          f"B claimed id={f1['b_id']} (rows={f1['b_claimed']})  "
          f"-> SAME row to two workers = {f1['a_id'] == f1['b_id'] and f1['a_claimed'] == f1['b_claimed'] == 1}")
    f2 = skip_locked_disjoint()
    print(f"2 skip locked:  A got id={f2['a_id']}, B got id={f2['b_id']}  "
          f"-> disjoint, no block = {f2['a_id'] != f2['b_id']}")
    f3 = conditional_update_exactly_once()
    print(f"3 conditional:  A returned {f3['a']}, B returned {f3['b']}  "
          f"-> exactly one winner = {len(f3['a']) == 1 and f3['b'] == []}")
    f4 = crash_then_redelivery()
    print(f"4 crash/redeliver: deliveries={f4['deliveries']}  "
          f"-> at-least-once, needs idempotency = {f4['deliveries'] == ['A', 'B']}")


if __name__ == "__main__":
    main()
