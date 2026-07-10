"""Tiny multi-tenant project-tracker API.

Users belong to orgs; projects belong to orgs; invoices belong to orgs.
Auth is faked via the X-User-Id header (see app.auth).

This is an INTENTIONALLY FLAWED fixture. Planted production-safety flaws are
marked with `# PLANTED: <card-id>` comments and nothing else. The rest of the
file (list, health, auth) is CLEAN contrast code.
"""
import asyncio
import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request

from .auth import get_current_user
from .db import get_conn

app = FastAPI(title="project-tracker")


@app.get("/health")
async def health() -> dict:
    # CLEAN: a properly awaited async call in an async handler.
    await asyncio.sleep(0)
    return {"status": "ok"}


@app.get("/projects")
def list_projects(user: dict = Depends(get_current_user)) -> dict:
    # CLEAN: parameterized query scoped to the caller's org from auth context.
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, org_id, name, status FROM projects WHERE org_id = ? ORDER BY id",
        (user["org_id"],),
    ).fetchall()
    return {"projects": [dict(r) for r in rows]}


@app.get("/projects/search")
def search_projects(q: str, user: dict = Depends(get_current_user)) -> dict:
    conn = get_conn()
    # PLANTED: sql-string-concat
    cur = conn.execute(
        f"SELECT id, org_id, name, status FROM projects "
        f"WHERE org_id = {user['org_id']} AND name LIKE '%{q}%' ORDER BY id"
    )
    return {"projects": [dict(r) for r in cur.fetchall()]}


@app.get("/projects/{project_id}")
def get_project(project_id: int, user: dict = Depends(get_current_user)) -> dict:
    conn = get_conn()
    # PLANTED: api-bola-id-swap / tenant-filter-forgotten
    row = conn.execute(
        "SELECT id, org_id, name, status FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="project not found")
    return dict(row)


@app.patch("/users/{user_id}")
def update_user(user_id: int, body: dict, user: dict = Depends(get_current_user)) -> dict:
    conn = get_conn()
    # PLANTED: api-mass-assignment
    columns = list(body.keys())
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [body[col] for col in columns]
    conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", (*values, user_id))
    row = conn.execute(
        "SELECT id, org_id, email, name, role FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return dict(row)


def _process_payment_event(event: dict) -> None:
    """Apply a payment webhook event: mark the referenced invoice paid."""
    conn = get_conn()
    invoice_id = event["invoice_id"]  # KeyError if the provider omits it
    conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))


@app.post("/webhooks/payment")
async def payment_webhook(request: Request) -> dict:
    body = await request.json()
    # PLANTED: python-swallowed-exception
    try:
        _process_payment_event(body)
    except Exception:
        pass
    return {"ok": True}


def _call_payment_provider(invoice_id: int, amount_cents: int) -> str:
    """Fake external payment provider. Simulates a blocking HTTP round-trip."""
    time.sleep(0.05)
    return f"pay_{invoice_id}_{amount_cents}"


@app.post("/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: int, user: dict = Depends(get_current_user)) -> dict:
    conn = get_conn()
    inv = conn.execute(
        "SELECT id, org_id, amount_cents, status FROM invoices WHERE id = ? AND org_id = ?",
        (invoice_id, user["org_id"]),
    ).fetchone()
    if inv is None:
        raise HTTPException(status_code=404, detail="invoice not found")

    # PLANTED: api-idempotency-missing-on-mutation-retry / db-transaction-around-network-call
    conn.execute("BEGIN")
    cur = conn.execute(
        "INSERT INTO payments (invoice_id, org_id, amount_cents, provider_ref, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (invoice_id, inv["org_id"], inv["amount_cents"], None,
         datetime.now(timezone.utc).isoformat()),
    )
    payment_id = cur.lastrowid
    provider_ref = _call_payment_provider(invoice_id, inv["amount_cents"])
    conn.execute("UPDATE payments SET provider_ref = ? WHERE id = ?", (provider_ref, payment_id))
    conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
    conn.execute("COMMIT")

    return {"invoice_id": invoice_id, "status": "paid", "provider_ref": provider_ref}
