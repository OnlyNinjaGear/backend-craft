# forward-test 112: observability-webhook (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. 12 targeted new tests covering every changed behavior: success metric/log/duration, three correlation-id cases including hostile header replacement, sentinel redaction at DEBUG across raw and JSON-formatted output, security_event tag assertions on two invalid-delivery paths, bool invoice-id guard with DB-state assertion, unknown invoice, duplicate-delivery idempotency (invoice state + zero payment rows), monkeypatched 500-with-traceback, and /metrics exposition. Grader re-ran the suite independently: 19 passed in 0.09s.

## Prompt

```text
Add metrics and logs for a new webhook processor.
```

## Round-2 focus verdict

Focus 1 (sentinel redaction test): PASS — real executable test at tests/test_webhook_observability.py:219-234, sentinel asserted absent from caplog.text and all formatted JSON lines; not a design comment. Focus 2 (tagged security/audit events): PASS — webhook.rejected event with distinct security_event='webhook.invalid_delivery' field at app/main.py:159-164, asserted in two tests; not a generic warning. Minor note: invoice_not_found gets an untagged warning, defensible since it is a structurally valid delivery and the reference targets rejected/invalid deliveries.

## References loaded

- SKILL.md
- observability-ops.md
- reliability-async.md
- api-contracts.md
- language-adapters.md
- codebase-fit.md
- testing-verification.md
- library-decisions.md

## Judge summary

Round 2 fully closes both round-1 regressions. The sentinel redaction requirement is met with a real test (sentinel in two payload locations, asserted absent from caplog at DEBUG and from formatted JSON lines), and invalid deliveries carry a distinct security_event field plus distinct event name, both asserted in tests. Correlation id, bounded labels, and no-payload-logging all hold with strong per-behavior tests. Routing matched the skill's table, the dependency gate was applied to prometheus-client, contract decisions were stated and tested, and the 19-passed proof reproduced exactly on independent re-run. Non-obvious failure modes (bool-as-int invoice id, request-id header forgery) plus a safe, idempotency-justified 500-on-transient-error contract earn the top score.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
End-to-end verified: correlation id `smoke-rid-1` flows request header → contextvar → JSON log line → response header; the invalid delivery gets a generated uuid, a `security_event` tag, and a bounded-label metric. Work complete.

## Result

Added metrics, structured logs, and correlation for the payment webhook processor in the FastAPI project-tracker, following the backend-craft skill (Continue mode: Impact Read, observability/reliability/api-contract/language-adapter/codebase-fit/testing references loaded).

### Files changed
- `app/observability.py` (new) — observability primitives:
  - `RequestIdMiddleware` (pure ASGI): accepts a well-formed inbound `X-Request-Id` (validated against `[A-Za-z0-9._-]{1,128}` to block log forgery/header injection; hostile values replaced with `uuid4().hex`), binds it to a `ContextVar`, echoes it on the response.
  - `RequestIdFilter` + `JsonLogFormatter`: one JSON object per line with `ts/level/logger/event/request_id` plus `extra=` fields; `configure_logging()` is idempotent.
  - Prometheus metrics on a dedicated `CollectorRegistry`: `webhook_events_total{provider,outcome}` counter and `webhook_processing_duration_seconds{provider}` histogram. Labels are bounded by design: `provider` static, `outcome` a closed set (`ok | invalid_payload | invoice_not_found | error`) — no ids, tenants, or raw error strings.
- `app/main.py` (modified) — instrumented `POST /webhooks/payment` and `_process_payment_event`; added `GET /metrics`; wired middleware/logging. The `except Exception: pass` swallow is gone: every delivery is counted, timed, and logged with stable identifiers only (`invoice_id`, event type truncated to 64 chars — never the payload). Invalid deliveries emit an explicitly tagged audit event (`security_event: webhook.invalid_delivery`). `_process_payment_event` now returns a bounded outcome, checks `rowcount` for unknown invoices, and rejects non-int/bool invoice ids (bool guard matters: `true` is an int subclass and would have targeted invoice 1).
- `tests/test_webhook_observability.py` (new) — 12 tests.
- `pyproject.toml` / `uv.lock` — `prometheus-client==0.25.0` added via `uv add` (lockfile-detected package manager). Library choice per the dependency gate: standard observability output; alternatives rejected: OpenTelemetry (needs collector/exporter infra this fixture lacks), hand-rolled counters (custom trace/metric code is a listed fragile pattern).

### Contract decisions (stated, tested)
- Unchanged: valid, invalid-payload, and unknown-invoice deliveries still return `200 {"ok": true}` — permanent errors are ACKed (retries can't fix them), now audit-logged and counted instead of silently dropped. The existing `test_webhook_returns_ok` passes unmodified.
- Additive: `X-Request-Id` response header; `GET /metrics` (deploy note in code: serve internal-only).
- One deliberate change: unexpected internal failures now propagate as 500 (previously swallowed → silent payment-event loss, a P1). Safe to invite provider redelivery because marking an invoice paid is idempotent — proven by `test_duplicate_delivery_is_idempotent`.

### Proof (outputs inspected)
- `uv run pytest -q` → **19 passed** (7 pre-existing + 12 new): success metric/log/duration, generated + propagated + hostile request-id, missing/bool invoice id, malformed JSON, unknown invoice, duplicate delivery idempotency, 500-with-traceback via monkeypatched processor, PII sentinel redaction (`SENTINEL-PAN-…` asserted absent from `caplog.text` and all formatted JSON lines), `/metrics` exposition.
- Smoke run inspected: JSON log line `{"event": "webhook.processed", "request_id": "smoke-rid-1", "outcome": "ok", "invoice_id": 1, "duration_ms": 0.28, ...}`; rejected delivery line carries `"security_event": "webhook.invalid_delivery"`; `/metrics` shows `webhook_events_total{outcome="ok",provider="payment"} 1.0` and `{outcome="invalid_payload"} 1.0`.

### Residual risks / out of scope (pre-existing fixture flaws, intentionally not fixed)
- Webhook has no signature verification (unauthenticated writes to `invoices`) — top hardening candidate.
- SQL injection in `GET /projects/search`; BOLA in `GET /projects/{id}`; mass assignment in `PATCH /users/{id}`; transaction held across the external provider call in `pay_invoice`.
- No alert definitions shipped (no alerting config exists in the repo); suggested first alert: rate of `webhook_events_total{outcome=~"error|invalid_payload"}` > 0 over 5m.
- SQLite in-memory, not a real DB engine, per project convention.

### Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/pyproject.toml
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/tests/test_app.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/012-python-fastapi/tests/conftest.py
````
