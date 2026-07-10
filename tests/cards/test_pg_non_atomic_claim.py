"""Verifier for pg-non-atomic-poll-queue-claim (needs a reachable PostgreSQL).

Four tests, one per fact proven by the reducer. If no PostgreSQL is reachable the
tests skip (they do not silently pass).

Run:
  PGHOST=/var/run/postgresql PGUSER=postgres PGDATABASE=bcdemo \
    uv run --with psycopg2-binary --with pytest \
    python -m pytest tests/cards/test_pg_non_atomic_claim.py -q
"""
import pytest

psycopg2 = pytest.importorskip("psycopg2")

from pg_non_atomic_claim import (  # noqa: E402
    conditional_update_exactly_once,
    crash_then_redelivery,
    non_atomic_double_claim,
    skip_locked_disjoint,
)


def _db_available() -> bool:
    try:
        import os
        c = psycopg2.connect(os.environ.get("BC_PG_DSN", ""))
        c.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="no reachable PostgreSQL")


def test_non_atomic_claim_double_delivers():
    r = non_atomic_double_claim()
    # both workers polled the same row and both UPDATEs claimed it
    assert r["a_id"] == r["b_id"]
    assert r["a_claimed"] == 1 and r["b_claimed"] == 1


def test_skip_locked_gives_disjoint_rows_without_blocking():
    r = skip_locked_disjoint()
    # each worker got a different pending row; B did not block on A's lock
    assert r["a_id"] != r["b_id"]
    assert {r["a_id"], r["b_id"]} == {1, 2}


def test_conditional_update_returning_claims_exactly_once():
    r = conditional_update_exactly_once()
    assert r["a"] == [(1,)]   # first writer wins
    assert r["b"] == []       # second writer's guard fails after A commits


def test_atomic_claim_is_not_exactly_once_across_a_crash():
    r = crash_then_redelivery()
    # claimed atomically, yet delivered twice after crash+requeue
    assert r["deliveries"] == ["A", "B"]
