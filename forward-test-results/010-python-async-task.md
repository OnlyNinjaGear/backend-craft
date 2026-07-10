# forward-test 010: python-async-task

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see ../docs/FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong: 6 new tests each map to a specific reliability claim (principal enrichment, no-principal path, failure-logged-not-swallowed with exc_info asserted and request unaffected, shutdown drain via lifespan exit, bounded-queue overflow drop-and-count under a deliberately stalled worker, enqueue-before-start loud drop); pytest output inspected; pre-existing contract test cited as unchanged. Verified independently: suite passes. Only gap is the absence of an explicit cancellation-propagation test, which the skill's verifier list names.

## Prompt

```text
In this Python async service, start a background enrichment task after each request.
```

## References loaded (from agent's 'Files read')

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md

## Judge summary

Exemplary answer, verified against the repo: explicit Impact Read, correct primary routing to reliability-async.md, no fire-and-forget tasks (lifespan-owned bounded worker pool with drop-and-count backpressure and a stated durable-outbox escalation path), bounded drain-then-cancel shutdown, logging.exception without catching CancelledError, sqlite off the event loop via to_thread, and a self-caught non-obvious failure mode (asyncio.Queue bound to the first lifespan's event loop, breaking restart). Proof is 6 targeted verifier tests mapping 1:1 to the reliability contract plus preserved contract tests; suite passes (58 passed re-run now). Deductions are minor: persistence-migrations.md not loaded despite adding migration 003, and cancellation propagation proven only implicitly rather than by a dedicated test.

## Misses

- Did not load references/persistence-migrations.md despite creating a new table + migration 003 (SKILL.md routing table maps the 'migration' signal to it); mitigated in practice by online-safety and rollback notes in the migration file
- No dedicated cancellation-propagation verifier: reliability-async.md lists 'cancellation test' as a verifier, but CancelledError propagation is only implicitly proven via lifespan teardown in other tests

## Changes needed in skill/reference/failure card

- In references/reliability-async.md, add a cross-reference rule: 'If the background work persists data (new table, outbox, event log), also load references/persistence-migrations.md before writing the migration' — makes the migration routing signal fire even when the entry point was a queue/worker task
- In references/reliability-async.md Verifiers section, make the cancellation verifier prescriptive for owned worker pools: 'assert a cancelled worker task exits (task.cancelled() is True / stop() completes within drain_timeout) with a dedicated test, not only via lifespan teardown'

## Tested agent answer (verbatim)

````text
All 48 tests pass, including the pre-existing contract tests (`test_existing_api_contract_unchanged`) and the tests added concurrently by other work in the repo. Final verification output: `48 passed, 1 warning in 0.23s`.

# Result

## What was built

A background request-enrichment pipeline for the FastAPI service at `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi`: after each HTTP request, a lightweight event (method, path, status, duration, raw `X-User-Id` header) is enqueued; app-owned background workers resolve the header into a server-side `(user_id, org_id)` principal and record an enriched row in a new append-only `request_events` table — entirely off the request path.

## Impact Read (per backend-craft)

1. **Public contracts:** unchanged — middleware only observes; contract test passes.
2. **Data:** new append-only table `request_events` (migration 003, online-safe: brand-new table, no lock on hot tables, documented rollback); reads `users` for enrichment.
3. **Principal/tenant:** `org_id`/`user_id` resolved server-side via parameterized lookup; the raw header is never trusted as a principal; NULL for unauthenticated requests.
4. **Side effects:** the core risk — work outliving the request. Addressed with the reliability rules below.
5. **Tests:** existing pytest suite + 6 new verifier tests.

## Design decisions (mapped to skill rules)

- **Owned lifecycle, not fire-and-forget:** no `asyncio.create_task` in handlers. Workers are started in the FastAPI `lifespan` and drained (bounded by `drain_timeout`) then cancelled on shutdown ("do not create untracked background tasks in request handlers").
- **Bounded concurrency:** fixed worker pool (2) + bounded queue (1000). Overflow policy is drop-and-count with a warning log — enrichment is best-effort/at-most-once and must never block or fail a response. Comment documents the escalation path: if enrichment ever becomes must-happen, use a durable outbox/queue, not an unbounded in-memory one.
- **No swallowed exceptions:** per-event failures use `logging.exception` (traceback preserved); `except Exception` deliberately does not catch `CancelledError`, so shutdown cancellation propagates out of the worker loop.
- **Time budgets & event loop:** each job runs under `asyncio.timeout(5)`; the blocking `sqlite3` write runs via `asyncio.to_thread` so the loop never blocks (comment notes `to_thread` can't cancel a dispatched statement mid-flight — acceptable at microsecond scale).
- **Restart-safe:** the `asyncio.Queue` is created in `start()`, not `__init__` — my first version bound the queue to the first lifespan's loop and broke on the next loop; the new tests caught this and it's fixed.
- **Codebase fit:** raw stdlib sqlite3 with parameterized SQL, migration as `NNN_*.sql` (auto-applied by `app/db.py`), module named by domain capability (`enrichment`, not `utils`), CLEAN-contrast comment style preserved.

**Assumptions stated:** "enrichment" = resolving the raw auth header into a principal and persisting an enriched request-activity record; it is telemetry, not business state, so at-most-once + load-shedding is the correct backpressure policy; all requests (including `/health`) are recorded to match "after each request" literally — excluding probe paths is a one-line filter if wanted.

## Files changed

- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/enrichment.py` — new: `RequestEvent`, `RequestEnricher` (start/stop lifecycle, bounded queue, workers, `wait_idle` test/ops sync point).
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py` — lifespan owning the enricher; `@app.middleware("http")` enqueues after every request (records 500 + re-raises on unhandled handler errors); `app.state.enricher` exposed.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/003_add_request_events.sql` — new table + production/rollback notes.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py` — client fixture now context-managed (lifespan runs) and depends on `fresh_db` so workers stop before DB reset.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_enrichment.py` — new: 6 tests.

## Proof (final proof contract)

`.venv/bin/python -m pytest -v` → **48 passed, 0 failed** (inspected output). New verifiers, all PASSED:
- `test_request_records_event_enriched_with_principal` — enrichment resolves user 1 → org 1
- `test_unauthenticated_request_recorded_without_principal`
- `test_enrichment_failure_does_not_fail_request_and_is_logged` — request stays 200; `logger.exception` record with `exc_info` asserted
- `test_shutdown_drains_pending_events` — graceful-shutdown drain
- `test_queue_overflow_drops_and_counts_instead_of_blocking` — bounded-concurrency/backpressure verifier
- `test_enqueue_before_start_drops_loudly` — missing-lifespan guard

Contract preservation: pre-existing `test_existing_api_contract_unchanged` and all other pre-existing tests pass unchanged.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/001_init.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/002_add_invoice_currency.sql
````
