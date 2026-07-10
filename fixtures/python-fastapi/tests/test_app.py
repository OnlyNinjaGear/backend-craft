"""Happy-path tests. These prove the API runs and the documented flows work.

They deliberately do NOT assert the planted flaws are absent — a code-review
skill / Semgrep ruleset is what should catch those.
"""
from tests.conftest import ALICE, BOB

from app import db


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_own_projects(client):
    resp = client.get("/projects", headers=ALICE)
    assert resp.status_code == 200
    projects = resp.json()["projects"]
    assert len(projects) == 2
    assert {p["name"] for p in projects} == {"Acme Website", "Acme Mobile App"}
    assert all(p["org_id"] == 1 for p in projects)


def test_search_works(client):
    resp = client.get("/projects/search", params={"q": "Acme"}, headers=ALICE)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["projects"]}
    assert names == {"Acme Website", "Acme Mobile App"}


def test_webhook_returns_ok(client):
    resp = client.post("/webhooks/payment", json={"invoice_id": 1, "event": "charge.succeeded"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_patch_updates_name(client):
    resp = client.patch("/users/1", json={"name": "Alice Cooper"}, headers=ALICE)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice Cooper"


def test_pay_creates_payment(client):
    resp = client.post("/invoices/1/pay", headers=ALICE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "paid"
    assert body["provider_ref"] == "pay_1_5000"

    conn = db.get_conn()
    count = conn.execute(
        "SELECT COUNT(*) AS n FROM payments WHERE invoice_id = 1"
    ).fetchone()["n"]
    assert count == 1


def test_unknown_user_is_rejected(client):
    # CLEAN contrast: auth fails closed for an unknown principal.
    resp = client.get("/projects", headers={"X-User-Id": "999"})
    assert resp.status_code == 401
