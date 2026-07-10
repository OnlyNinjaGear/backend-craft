# forward-test 012: observability-webhook

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see ../docs/FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong: 10 targeted tests including an adversarial cardinality test (random event string asserted absent from /metrics exposition), correlation-id propagation smoke, traceback-preservation assertion on the failure path, duplicate-delivery idempotency check, and full-suite run (58 passed, independently reproduced by the grader). Matches the observability-ops.md verifier list except for a missing explicit log-redaction test.

## Prompt

```text
Add metrics and logs for a new webhook processor.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/observability-ops.md
- references/reliability-async.md
- references/api-contracts.md
- references/codebase-fit.md
- references/language-adapters.md
- references/library-decisions.md

## Judge summary

Near-exemplary run. The agent ran the Impact Read, routed to exactly the right six references per the SKILL.md table, and produced a safe, verified implementation: bounded-cardinality metrics with an allowlist defeating attacker-minted label values (the non-obvious failure mode, proven by an adversarial test), correlation ids propagated request→response→logs, no payload logging, and the planted python-swallowed-exception made observable without breaking the 200-ack contract (contract changes explicitly enumerated, retry implication escalated as P1 alongside the missing-signature P1). Proof claims were independently verified: all changed files exist as described and 'uv run pytest -q' reproduces 58 passed. Only strict-mode gaps: no dedicated log-redaction test (a verifier the reference itself lists) and failure logs are not explicitly tagged as security/audit events, though failures are fully observable. These are reference-wording weaknesses more than agent errors; score 4.

## Misses

- no explicit log-redaction test: observability-ops.md lists 'log redaction test' as a verifier, but no test asserts the raw payload body is absent from captured log output (the cardinality test only covers metrics exposition)
- failure events are logged/counted but never explicitly framed or tagged as security/audit events (e.g. a distinct audit field or security event category for rejected deliveries)

## Changes needed in skill/reference/failure card

- observability-ops.md Verifiers section: change 'log redaction test' to a concrete contract, e.g. 'a test that sends a payload containing a sentinel secret/PII value and asserts the sentinel never appears in captured log output' — the vague phrasing let the agent satisfy redaction by design comment instead of by test
- observability-ops.md 'security/audit events' bullet in the Observability read: add one sentence defining what qualifies (rejected/unauthenticated/invalid deliveries must emit an explicitly tagged security event, not just a generic warning), so agents name and tag audit events rather than covering them implicitly

## Tested agent answer (verbatim)

````text
## Result

Instrumented the payment webhook processor (`POST /webhooks/payment`) in the fixture at `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi` with structured logs, Prometheus metrics, and per-delivery correlation ids, following the backend-craft skill (Continue mode: Impact Read, then `observability-ops.md`, `reliability-async.md`, `api-contracts.md`, `codebase-fit.md`, `language-adapters.md`, `library-decisions.md`).

### Files changed
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/observability.py` (new) — metric definitions, event-type allowlist bounding, `record_webhook_result()`, stdlib JSON log formatter, idempotent `configure_logging()`.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py` — instrumented `payment_webhook` + `_process_payment_event` (now returns whether a row was applied), added `GET /metrics` exposition endpoint.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_webhook_observability.py` (new) — 10 tests.
- `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml` + `uv.lock` — added `prometheus-client==0.25.0` via `uv add` (library-decisions gate: "standard observability output" justifies the dependency; chosen over OpenTelemetry because the fixture has no collector infrastructure and needs only counters/histograms + a scrape endpoint; removable by deleting `observability.py`'s metric block and `/metrics`).

### Design
Metrics (all labels bounded — no invoice ids, user ids, correlation ids, or raw error strings as label values):
- `webhook_events_total{provider, event_type, outcome}` — outcome ∈ {processed, noop, failed, invalid}; event_type is collapsed through the allowlist `{charge.succeeded, charge.failed, charge.refunded}` → else `"other"`, so attacker/provider-controlled strings cannot mint label cardinality.
- `webhook_event_failures_total{provider, error_code}` — error_code ∈ {invalid_json, invalid_payload, missing_field, processing_error}.
- `webhook_processing_seconds{provider}` histogram.

Logs (stdlib `logging`, JSON lines, no payload dumps): stable fields `correlation_id`, `provider`, `event_type` (bounded), `invoice_id`, `outcome`, `error_code`; failures use `logger.exception` so the traceback is preserved — the planted `except Exception: pass` no longer swallows silently (`except Exception`, not `BaseException`, so cancellation still propagates).

Correlation: each delivery uses incoming `X-Request-Id` or a generated uuid; echoed in the response header (including 400s) and present in every log line.

### Behavior changes (explicit)
- Public success contract preserved: `{"ok": True}` with 200, and failures are still acked with 200 (pre-existing behavior kept deliberately; now observable instead of silent). Existing `test_webhook_returns_ok` still passes.
- Malformed JSON now returns 400 `{"detail": "invalid JSON body"}` (was an unhandled 500); non-object JSON returns 400 (was swallowed 200). Both use the app's existing `detail` error shape, are counted/logged, and are covered by tests.

### Proof (final proof contract)
- `uv run pytest -q` → **58 passed** (10 new observability tests + full pre-existing suite).
- Smoke request: response `x-request-id: smoke-42` matches the emitted log line `{"level":"INFO","message":"payment webhook event processed","correlation_id":"smoke-42","event_type":"charge.succeeded","invoice_id":1,"outcome":"processed"}`; failure path emits an ERROR record with full traceback and `error_code:"missing_field"`; `/metrics` exposes exactly the bounded series, e.g. `webhook_events_total{event_type="charge.succeeded",outcome="failed",provider="payment"} 1.0`.
- Cardinality verifier: test posts a random event string and asserts it lands in `event_type="other"` and never appears in the exposition output.

### Out-of-scope findings flagged (not implemented)
- P1: webhook has no signature/authenticity verification — any caller can mark invoices paid.
- P1: acking failures with 200 means the provider never retries; proper fix is 5xx on transient failure + idempotent reprocessing (state transition is already idempotent; duplicate-delivery test included).
- P2: `/metrics` is on the public listener; should be internal-only in a real deployment (noted in code comment).
- Other planted flaws (`sql-string-concat` in search, pay-invoice idempotency/transaction-around-network-call) left untouched — outside this task's scope.

### Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py (twice: original and concurrently-updated version)
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/enrichment.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py (twice: original and concurrently-updated version)
````
