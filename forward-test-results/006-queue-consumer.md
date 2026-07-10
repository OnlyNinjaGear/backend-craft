# forward-test 006: queue-consumer

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see ../docs/FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Full-suite run (29 passed) plus 11 targeted tests whose names map one-to-one to the changed behaviors: duplicate delivery yields one email, retry/backoff timing with injected clock (no sleeps), dead-letter exhaustion, poison-without-retry, cross-tenant dead-letter, visibility-timeout requeue, and graceful thread shutdown. Grader independently re-ran the tests (11 passed) and confirmed the assertions match the claims — the duplicate test checks both the email count and the inbox row count across a second drain. Migration proof (CREATE-only, exercised per test run, DROP TABLE rollback) matches the final proof contract.

## Prompt

```text
Implement a worker that consumes invoice events and emails customers.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/reliability-async.md
- references/codebase-fit.md
- references/language-adapters.md
- references/persistence-migrations.md
- references/observability-ops.md
- references/testing-verification.md

## Judge summary

Top-band answer. The agent ran a substantive impact read (avoided the planted-flaw surface in main.py, noted the 001_init.sql large-table lock warning and made the migration CREATE-only, scoped invoice lookups by org in contrast to the planted BOLA flaw), routed to six correct reference files, and implemented a transactional-inbox worker hitting every expected behavior: at-least-once assumption, dual dedupe (event_id UNIQUE + idempotent state transition), bounded jittered retries, dead-letter for poison, graceful shutdown, and no transaction across the network send. It found non-obvious failure modes: the crash window between send and mark-sent (mitigated via provider idempotency key, honestly documented as residual at-least-once risk), stranded 'processing' rows recovered by visibility timeout, concurrent-worker double-claim prevented by rowcount-checked CAS, and skipped-vs-dead disambiguation. Proof is real: I independently re-ran the 11 named tests (all pass) and spot-checked the implementation matches every claim, including the duplicate-delivery test asserting exactly one email and one row. Sole deduction candidate is not loading auth-tenancy-security.md despite tenant/PII signals, but the corresponding behaviors were implemented correctly regardless, so it does not lower the score.

## Misses

- Minor routing gap only: did not load references/auth-tenancy-security.md despite tenant/PII signals (emails customers, cross-tenant invoice references, email addresses in logs) per the SKILL.md routing row 'auth, role, permission, tenant, PII' — though the resulting behavior (org-scoped invoice lookup, cross-tenant dead-letter, redact_email in logs) was correct anyway

## Changes needed in skill/reference/failure card

- Add a cross-reference in references/reliability-async.md (queue-consumer section): 'Workers that send user-facing communications (email/SMS/push) touch PII and tenant boundaries — also load references/auth-tenancy-security.md', so the tenant/PII routing row fires even when the task reads as pure reliability work

## Tested agent answer (verbatim)

````text
## Deliverable: invoice-email worker for the python-fastapi fixture

### What was built

A DB-backed inbox queue plus a bounded, idempotent worker that consumes invoice events and emails the owning org's billing contact.

**New/changed files (all absolute paths):**

- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/004_invoice_events.sql` — new `invoice_events` inbox table: producer-supplied `event_id UNIQUE` (ingestion dedupe), `status` state machine (`pending → processing → sent | skipped | dead`), `attempts`, `next_attempt_at`, `claimed_at`, `last_error`, plus a `(status, next_attempt_at)` index matching the claim query. CREATE-only on a new empty table, so it takes no locks on the large `invoices`/`payments` tables (per the production note in `001_init.sql`).
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/emailer.py` — email boundary: `EmailClient` Protocol (`send(to, subject, body, idempotency_key, timeout)`), `EmailTransientError` vs `EmailPermanentError` taxonomy, `ConsoleEmailClient` default, `redact_email()` for PII-safe logs.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/invoice_email_worker.py` — `record_invoice_event()` publisher (INSERT OR IGNORE dedupe, returns False on duplicate delivery) and `InvoiceEmailWorker` (claim → send → mark), template dispatch for `invoice.paid` / `invoice.created`, plus a `python -m app.invoice_email_worker` entrypoint.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py` — minimal change: apply all `migrations/*.sql` in sorted order instead of only `001_init.sql`.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_invoice_email_worker.py` — 11 tests with injected clock/RNG (no sleeps for backoff).

### Design decisions mapped to skill rules

- **At-least-once, idempotent consumer** (`reliability-async.md`): dedupe at ingestion via `event_id UNIQUE`; idempotent state transition means an already-`sent` event can never be re-claimed; the `event_id` is passed to the email client as `idempotency_key` so a provider can dedupe the crash-between-send-and-mark window (documented as at-least-once email without provider support).
- **No transaction across network calls** (`persistence-migrations.md`): claim is a single short compare-and-swap `UPDATE ... WHERE id=? AND status='pending'` (rowcount-checked so concurrent workers can't double-claim); the email send happens outside any transaction; outcome recorded with another short write.
- **Bounded retries**: `max_attempts` (default 5, tests use 3), exponential backoff `base * 2^(attempt-1)` capped at `backoff_cap_seconds`, jitter `uniform(0.8, 1.2)`. Permanent failures (unknown invoice, tenant mismatch, no recipient, malformed payload, provider 5xx-permanent) dead-letter immediately — no retry of hopeless work.
- **Dead-letter strategy**: poison messages and exhausted retries land in `status='dead'` with `last_error` for operator inspection/replay; unknown-but-well-formed event types get `status='skipped'` so they're distinguishable from poison.
- **Bounded concurrency and lifecycle**: one owned consumer thread (`start()`/`stop(timeout)`, graceful shutdown, no untracked background work), `max_batch` bound per poll, and a visibility-timeout re-queue for events stranded in `processing` by a crash.
- **Timeouts**: every send gets `send_timeout_seconds` passed to the client adapter.
- **No swallowed exceptions** (`language-adapters.md`, contrast to the planted webhook flaw): specific exception classes; unexpected errors use `logger.exception` (traceback preserved) and are retried bounded by `max_attempts`; a failing poll never kills the consumer thread but is logged, and the poll wait prevents a hot error loop.
- **Tenant scoping**: invoice lookup is `WHERE id = ? AND org_id = ?` (contrast to the planted BOLA flaw); a cross-tenant event reference dead-letters instead of emailing the wrong tenant.
- **Observability** (`observability-ops.md`): every log line carries `event_id` (correlation id), `invoice_id`, `org_id`, `attempt`; recipient addresses redacted; bodies never logged.
- **Codebase fit**: flat `app/` modules, raw parameterized sqlite3, ISO-8601 UTC strings, existing `fresh_db` test fixture — no new dependencies, no ORM, no framework imposed. `app/main.py` was deliberately not modified (it is the planted-flaw surface); producers call `record_invoice_event()`.

### Assumptions (stated, not asked)

1. No message broker exists in the fixture, so the queue is a transactional-inbox table — the most testable at-least-once substrate here; the worker is broker-agnostic if one is added later.
2. "Customer" = the org's billing contact, approximated as the earliest admin user of the invoice's org (fallback: earliest user; none → dead-letter). The schema has no explicit billing-contact column.
3. Producers (webhook/pay endpoint) are not wired up to publish, to avoid touching intentionally planted code; `record_invoice_event()` is the integration point.
4. The standalone `main()` entrypoint is nominal only in this fixture (per-process in-memory SQLite); in production it would point at the shared DB.

### Proof (final proof contract)

- Full suite: `uv run pytest -q` → **29 passed** (includes 12 pre-existing app tests and 6 tests added by concurrent sessions — no regressions from the `db.py` multi-migration change).
- New worker tests, all PASSED (output inspected): `test_paid_event_emails_org_billing_contact` (asserts recipient `alice@acme.test`, `$50.00` body, idempotency key, timeout, `status=sent`), `test_event_for_other_org_emails_that_orgs_contact`, `test_duplicate_delivery_is_ingested_once_and_emailed_once`, `test_transient_failure_retries_with_backoff_then_succeeds` (asserts not-due-before-backoff, attempts=3, exactly one email), `test_transient_failures_exhaust_to_dead_letter`, `test_unknown_invoice_is_poison_and_dead_letters_without_retry`, `test_cross_tenant_invoice_reference_dead_letters`, `test_permanent_email_error_dead_letters_without_retry`, `test_unknown_event_type_is_skipped_not_dead`, `test_stuck_processing_event_is_requeued_after_visibility_timeout`, `test_worker_thread_processes_and_shuts_down_gracefully`.
- Migration proof: applied on every test run via rebuilt in-memory DB (up-run exercised 29 times); CREATE-only, forward-fix is `DROP TABLE invoice_events`.

### Residual risks

- Exactly-once email requires provider-side idempotency support; without it the contract is at-least-once (crash window between send and mark-sent).
- SQLite fixture semantics (single shared autocommit connection) differ from production Postgres; the claim CAS pattern translates directly to `UPDATE ... RETURNING` / `SELECT ... FOR UPDATE SKIP LOCKED` there.
- Concurrent harness sessions were mutating this fixture during the work (`002_add_invoice_currency.sql`, `003_add_request_events.sql`, extra tests appeared); I renumbered my migration to `004` to avoid a duplicate-prefix collision and re-verified the full suite green afterwards.

### Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py (twice: original and concurrently-modified state)
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/001_init.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
````
