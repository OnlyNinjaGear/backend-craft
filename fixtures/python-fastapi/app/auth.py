"""Fake auth: the X-User-Id header resolves the current user + org from the DB.

This module is CLEAN contrast code: the lookup is parameterized and the
missing/unknown-user paths fail closed with an explicit 401.
"""
from fastapi import Header, HTTPException

from .db import get_conn


def get_current_user(x_user_id: str | None = Header(default=None)) -> dict:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="missing X-User-Id header")

    conn = get_conn()
    # CLEAN: parameterized query, value bound as a parameter (not concatenated).
    row = conn.execute(
        "SELECT id, org_id, email, name, role FROM users WHERE id = ?",
        (x_user_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return dict(row)
