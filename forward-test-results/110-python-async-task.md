# forward-test 110: python-async-task (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Excellent. Nine new tests map one-to-one to the reliability contract, including the exact dedicated cancellation shape the reference demands (hung job, timed stop(), task.cancelled() asserted per worker), bounded-concurrency measurement (max in-flight == worker count under burst), overflow drop without block/raise, poison-event survival, duplicate-delivery idempotency at the DB row level, drain-on-shutdown, end-to-end org attribution, and fail-open submit before start. Tests drive asyncio directly via asyncio.run with injected process functions — deterministic, no sleeps-as-synchronization except brief handoff waits. Grader reproduced 16 passed in 0.26s. The proof contract's 'inspect output' and 'files changed match reality' requirements both hold on inspection of the working tree.

## Prompt

```text
In this Python async service, start a background enrichment task after each request.
```

## Round-2 focus verdict

FOCUS 1 (persistence -> persistence-migrations.md loaded): PASS — reference listed in Files read and its content demonstrably applied (additive migration with rollback note, ON CONFLICT idempotency key, deploy-before-code ordering). FOCUS 2 (dedicated cancellation test): PASS — test_stop_cancels_workers_within_drain_timeout is a standalone pool test asserting all worker tasks report cancelled() and stop() completes within the drain timeout; lifespan teardown is covered by a separate, additional test. Both verified against actual files and a fresh test run, not just the agent's report.

## References loaded

- SKILL.md
- references/reliability-async.md
- references/language-adapters.md
- references/persistence-migrations.md
- references/observability-ops.md

## Judge summary

Round-2 fixes verified working end-to-end. The agent loaded persistence-migrations.md when adding the request_events table/migration (focus 1) and shipped a genuine dedicated cancellation test asserting task.cancelled() and stop() within the drain timeout, separate from lifespan teardown (focus 2). Core expectations all met: owned bounded worker pool instead of fire-and-forget create_task, drain-then-cancel shutdown, poison-event isolation, re-raised CancelledError, idempotent persistence. Grader independently re-ran the suite: 16 passed, matching the claimed proof. Two non-obvious failure modes were caught via real test runs (event-loop binding of asyncio primitives; TestClient skipping lifespan). Only P3-level routing misses (testing-verification.md, auth-tenancy-security.md not loaded) with no quality impact. Score 4; both round-2 focus items closed.

## Misses

- testing-verification.md not loaded despite authoring 9 new tests (routing row 'tests, CI, contract testing, DB integration tests' arguably matches); mitigated because reliability-async.md's own required-verifier list was followed exactly
- auth-tenancy-security.md not loaded although the new request_events table stores per-org/user attribution resolved from a raw header; implementation is nonetheless fail-safe (NULL on unknown user, parameterized lookups), so no defect resulted

## Changes needed

- Continue mode in SKILL.md could mirror Retrofit mode's explicit rule 'when the plan prescribes new tests, load references/testing-verification.md' — currently only Retrofit mode states it, so feature work that ships new verifiers can skip that reference while technically matching the routing row. Otherwise none: both round-2 cross-links (reliability-async -> persistence-migrations at lines 34/64, dedicated cancellation test at lines 94-96) demonstrably fired.

## Tested agent answer (verbatim)

````text
## Background enrichment after each request — delivered

### Impact Read (per backend-craft)
- **Contracts:** unchanged — enrichment is post-response, best-effort; no response fields or status codes touched.
- **Data:** new additive table `request_events` (migration `002`), idempotent writes.
- **Tenancy:** events carry user/org attribution resolved via parameterized lookups; missing/unknown users stored as NULL, never guessed.
- **Side effects outliving the request:** the core risk — solved with an owned, bounded worker pool, not fire-and-forget `asyncio.create_task`.

### Design
- **`app/enrichment.py` (new)** — `EnrichmentWorkerPool`: 2 worker tasks consuming an `asyncio.Queue(maxsize=100)`. Workers are owned (references held, cancelled and awaited in `stop()`), started/stopped from the FastAPI lifespan — never spawned per request. Each job runs under `asyncio.timeout(5s)`; failures are logged with traceback and isolated (poison event can't kill a worker); `CancelledError` is re-raised, never swallowed. The blocking sqlite write runs in `asyncio.to_thread`. Queue and workers are built in `start()` (not `__init__`) because asyncio primitives bind to a loop — the pool is restartable across loops (this bug was caught by the first test run and fixed).
- **`app/main.py`** — lifespan starts the pool and stops it with a 5s drain deadline; an `http` middleware submits a `RequestEvent` after each response. `submit()` never blocks and never raises: on full queue or stopped pool it drops the event with a warning log (enrichment is best-effort; the request path is never failed or slowed). Correlation id honors inbound `X-Request-Id`, else `uuid4`.
- **Enrichment job** — resolves the raw `X-User-Id` header into `user_id`/`org_id` from the DB, persists to `request_events` with `ON CONFLICT(request_id) DO NOTHING` — the request id is the idempotency key, so at-least-once/duplicate submission yields exactly one row.
- **`migrations/002_request_events.sql` (new)** + `app/db.py` now applies all `migrations/*.sql` in filename order. Additive-only, deployable before the code, rollback = `DROP TABLE`.
- **`tests/conftest.py`** — `client` fixture now uses `with TestClient(app)` so the lifespan actually runs (the pool would otherwise silently never start in tests).

### Proof (final proof contract)
`uv run pytest` (lockfile-detected package manager): **16 passed** — 7 pre-existing tests unchanged and green, 9 new verifiers, stable across 3 consecutive runs. New verifiers map to the skill's required list:
- `test_stop_cancels_workers_within_drain_timeout` — dedicated cancellation test: `stop()` returns within the drain timeout and `task.cancelled()` is true for every worker (not implicit lifespan teardown).
- `test_concurrency_is_bounded_by_worker_count` — max in-flight == worker count under a 10-job burst.
- `test_queue_overflow_drops_without_blocking` — full queue → `submit()` returns `False`, no block/raise.
- `test_poison_event_does_not_kill_worker` — worker survives a raising job and processes the next one.
- `test_duplicate_submission_is_idempotent` — duplicate delivery → 1 row.
- `test_shutdown_drains_pending_events` — graceful shutdown flushes queued events.
- `test_request_produces_enriched_event` / `test_unauthenticated_request_still_recorded` — end-to-end org attribution and anonymous path.
- `test_submit_before_start_drops_safely` — fail-open before startup.

### Assumptions
- "Enrichment" concretized as: capture raw request facts at the boundary, enrich with user/org attribution in the background, persist to `request_events`. Swap `_enrich_and_store` for a real enrichment call without touching the pool.
- Drop-on-overflow (not backpressure) is correct for best-effort analytics; the drop is logged with the request id.
- Enrichment shares the single fixture sqlite connection (autocommit); acceptable here since Python's sqlite3 runs serialized. A real service would use a pooled DB or a durable queue.

### Noted, deliberately not changed (pre-existing fixture flaws, out of scope)
`app/main.py`: SQL string interpolation in `/projects/search` (line 43–44), missing org scoping in `GET /projects/{id}` (line 52), mass-assignment `PATCH /users/{id}` with no auth check (line 61–67), `except Exception: pass` webhook (line 87), blocking `time.sleep` + transaction held across the external payment call (line 94, 108–119). These are the fixture's intentional review targets.

### Files changed
- `app/enrichment.py` (new), `migrations/002_request_events.sql` (new), `tests/test_enrichment.py` (new)
- `app/main.py`, `app/db.py`, `tests/conftest.py` (modified)

All under `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/`.

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/pyproject.toml
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/tests/test_app.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/tests/conftest.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/010-python-fastapi/migrations/001_init.sql
````
