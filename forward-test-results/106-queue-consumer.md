# forward-test 106: queue-consumer (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. 17 targeted tests covering duplicate delivery (exactly one email), backoff window and no-early-reclaim, dead-letter after max_attempts, poison event with batch continuation, tenant redirect prevention, org-ownership, permanent no-recipient, send timeout as transient, stale vs fresh claim requeue, graceful stop, and a dedicated cancellation test asserting task.cancelled() — precisely the verifier shape reliability-async.md demands. Proof independently reproduced (24 passed, 0.79s) plus compileall and an end-to-end lifespan run with masked-PII log evidence.

## Prompt

```text
Implement a worker that consumes invoice events and emails customers.
```

## Round-2 focus verdict

FOCUS (loads auth-tenancy-security.md via new cross-link from reliability-async.md): PASS — file listed in Files read, and applied, not just loaded: server-side tenant-scoped recipient resolution ordered admin-first, event payload explicitly untrusted for addressing, org-scoped invoice lookup (id, org_id), mask_email keeping recipient PII out of logs, and dedicated tests test_recipient_comes_from_invoice_org_not_event_payload and test_event_org_must_own_invoice.

## References loaded

- SKILL.md
- reliability-async.md
- persistence-migrations.md
- auth-tenancy-security.md
- language-adapters.md
- testing-verification.md
- codebase-fit.md

## Judge summary

Round-2 regression is closed. The reliability-async.md fix (cross-link: worker sending user-facing email -> load auth-tenancy-security.md) is present at lines 59-63 and the tested agent followed it — auth-tenancy-security.md appears in Files read and its content shaped the design (tenant-scoped recipient resolution, untrusted payload, PII-masked logs, tenant tests). The implementation itself is exemplary: transactional outbox with atomic claim, at-least-once with email_log dedupe, backoff+jitter, dead-lettering, visibility-timeout requeue, graceful shutdown with clean cancellation, and 17 new tests including the exact dedicated cancellation verifier the reference prescribes. I independently re-ran the suite: 24 passed. Deliberately left the fixture's planted flaws untouched while noting them. Full 4: non-obvious failure modes (stale claims, transport/log crash window, shared-connection hazard) + safe implementation + inspected proof.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
Implementation complete and verified. Final report:

## What was built

A DB-backed (transactional-outbox) invoice-event email worker for the FastAPI/SQLite project-tracker at `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi`. No broker exists in this fixture, so events live in a new `invoice_events` table; producers append in the same transaction as the invoice state change, and an asyncio worker polls, claims, emails, and records delivery.

**New files**
- `migrations/002_invoice_events.sql` — `invoice_events` outbox (status/attempts/next_attempt_at/claimed_at/last_error, index on the poll shape) + `email_log` with `UNIQUE(event_id)` as the idempotency marker. New tables only — no ALTER on the large `invoices`/`payments` tables, so no online-DDL choreography needed; rollback is two DROPs.
- `app/events.py` — `publish_invoice_event(conn, ...)` parameterized outbox insert; joins the caller's open transaction.
- `app/emailer.py` — `EmailSender` protocol, `EmailMessage`, transient `EmailSendError`, `ConsoleEmailSender` dev transport, `mask_email` (logs never carry raw recipient PII).
- `app/worker.py` — `InvoiceEmailWorker`: state machine `pending → processing → sent | dead`; atomic single-statement claim (`UPDATE ... WHERE status='pending'`, rowcount-checked — never a DB transaction held across the send); at-least-once with `email_log` dedupe; bounded retries (default 5) with exponential backoff + jitter, cap, and dead-letter with `last_error`; permanent failures (unknown event type, invoice/org mismatch, no recipient) dead-letter immediately without retry; per-send budget via `asyncio.timeout` + `asyncio.to_thread`; stale-claim requeue with visibility timeout; graceful `stop()` and clean `CancelledError` propagation (claim released before re-raise); poison messages never kill the batch. Recipient is resolved server-side from the invoice's org (admin first, else first member) — event payload is never trusted for addressing, and the invoice lookup is org-scoped `(id, org_id)`. Standalone `python -m app.worker` entrypoint with SIGINT/SIGTERM handlers included (dev demo; in-memory DB makes lifespan the real deployment).
- `tests/test_invoice_email_worker.py` — 17 tests.

**Modified**
- `app/db.py` — applies all `migrations/*.sql` in sorted order instead of only `001_init.sql`.
- `app/main.py` — FastAPI lifespan starts/drains the worker (5s drain then cancel); `pay_invoice` publishes `invoice.paid` inside its existing BEGIN/COMMIT (outbox); `_process_payment_event` publishes after marking paid.

## Assumptions
- "Customer" = the invoice's org; billing contact = org admin, falling back to the first member.
- Email transport is injected via protocol; `ConsoleEmailSender` is the dev default (no SMTP config surface exists in this fixture).
- This project is an intentionally flawed review fixture (per pyproject description), so pre-existing planted flaws were deliberately left untouched (SQLi in `/projects/search`, missing tenant check on `GET /projects/{id}`, mass assignment in `PATCH /users/{id}`, unauthenticated webhook with swallowed exceptions, transaction held across the payment-provider call in `pay_invoice`). The new code does not depend on any of them.

## Proof
- `uv run --no-sync pytest -q` → **24 passed** (7 pre-existing + 17 new), 0.79s. New failing-path coverage: duplicate delivery sends exactly one email; transient failure reschedules with backoff in `(0, base]` and is not re-claimed early; dead-letter after `max_attempts` and never re-claimed; unknown event type dead-letters while the batch continues; payload email cannot redirect delivery (tenant test); event org must own invoice; missing recipient is permanent; slow send times out as transient; stale `processing` requeue (and fresh claim not requeued); graceful stop; dedicated cancellation test asserting `task.cancelled()`.
- `.venv/bin/python -m compileall app tests` → OK.
- End-to-end lifespan run: `POST /invoices/2/pay` → outbox row → lifespan worker delivered `Invoice #2 paid` to org-1 admin (log shows masked `a***@acme.test`), event `status=sent attempts=1`, clean shutdown.

## Residual risks
- The fixture shares one SQLite connection between request threads and the worker; a request's open `BEGIN` (pre-existing `pay_invoice` flaw) shares transaction state with worker statements. Real deployment needs a dedicated worker connection/pool (documented in `app/worker.py`).
- At-least-once: a crash in the window between transport hand-off and `email_log` insert can re-send once; documented and inherent without a transactional email provider or provider-side idempotency keys.
- `asyncio.to_thread` cannot force-kill a stuck transport thread; the timeout bounds the worker, not the thread (standard Python limitation).

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/pyproject.toml
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/app/__init__.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/migrations/001_init.sql
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/tests/conftest.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/006-python-fastapi/tests/test_app.py
````
