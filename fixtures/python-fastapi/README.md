# python-fastapi fixture — intentionally flawed

## Purpose

A tiny multi-tenant **project-tracker API** used as a fixture to forward-test the
`backend-craft` code-review skill and to exercise Semgrep checker rules.

Users belong to orgs; projects belong to orgs; invoices belong to orgs. Auth is
faked: the `X-User-Id` header resolves the current user + org from the seeded DB.
The database is raw stdlib `sqlite3` (no ORM), seeded in-memory at startup with
2 orgs, 2 users, 3 projects, and 3 invoices from `migrations/001_init.sql`.

This project is **intentionally flawed**. It contains exactly 5 planted
production-safety failures, each mapped to a `backend-craft` failure card and
marked in code with a `# PLANTED: <card-id>` comment and nothing else. The flaws
are runtime/production-safety flaws, **not** compile errors — the app runs and
the happy-path tests pass.

It also contains **clean contrast code** (a parameterized query, a properly
awaited async call, fail-closed auth) so checker false positives can be measured.

> Do not "fix" this project. The flaws are the point.

## Stack

Python 3.14 · FastAPI · raw `sqlite3` (stdlib) · `uv` for env/deps.

## How to run tests

```
cd /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi && uv run pytest -q
```

Expected: **7 passed**. The tests cover the happy path only (list own projects,
search, webhook ok, patch name, pay creates payment, health, auth rejects an
unknown user). They deliberately do **not** assert that the planted flaws are
absent.

## Layout

```
app/
  main.py        endpoints (contains all 5 planted flaws + clean contrast)
  auth.py        X-User-Id -> user/org resolution (CLEAN contrast)
  db.py          sqlite connection + seed
migrations/
  001_init.sql   schema; notes invoices/payments is large (10M+) in prod
tests/
  test_app.py    happy-path tests
  conftest.py    per-test DB reset + client fixtures
```

## Expected failures (planted)

| card id | file:line area | one-line description |
|---|---|---|
| `api-bola-id-swap` / `tenant-filter-forgotten` | `app/main.py:52` (`get_project`, marker :54) | `GET /projects/{id}` authenticates but fetches by `id` only — no org predicate, returns any org's project. |
| `sql-string-concat` | `app/main.py:41` (`search_projects`, marker :43) | `GET /projects/search?q=` builds SQL with an f-string interpolating `q` straight into `execute`. |
| `python-swallowed-exception` | `app/main.py:87` (`payment_webhook`, marker :89) | `POST /webhooks/payment` wraps processing in `try/except Exception: pass` and returns `{"ok": true}` regardless. |
| `api-mass-assignment` | `app/main.py:65` (`update_user`, marker :67) | `PATCH /users/{id}` writes every key of the JSON body into `users` via a dynamic `UPDATE` — client can set `role` or `org_id`. |
| `api-idempotency-missing-on-mutation-retry` + `db-transaction-around-network-call` | `app/main.py:104` (`pay_invoice`, marker :113) | `POST /invoices/{id}/pay` opens a txn, inserts a payment row, calls the fake payment provider (blocking `time.sleep`) **inside** the txn, then commits; no idempotency key, so a retry duplicates the payment. |

## Clean contrast code (should NOT be flagged)

- `app/auth.py` — parameterized `SELECT ... WHERE id = ?`, fail-closed 401s.
- `app/main.py` `list_projects` — parameterized query scoped to `user["org_id"]`.
- `app/main.py` `health` — a properly awaited async call.
- `app/main.py` `get_project` / `pay_invoice` — correct `404` handling on missing rows.
