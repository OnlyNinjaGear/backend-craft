# forward-test 004: payment-idempotency

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/go-http
Score: 3/4
Generic advice: False
Verifier quality (judge): Excellent. Named tests match the changed behavior exactly and were verified to exist and assert the right things: TestCheckoutDuplicateRequestChargesOnce checks provider callCount == 1, byte-identical replay, and exactly one paid order; TestCheckoutClientRetryAfterExhaustedAttemptsChargesOnce covers the cross-request retry path; concurrent-duplicate and bounded-backoff tests cover the race and retry policy. Run under -race with go vet/gofmt clean, outputs inspected, and independently reproduced by this grader (16 tests pass).

## Prompt

```text

```

## References loaded (from agent's 'Files read')

- references/reliability-async.md
- references/api-contracts.md
- references/language-adapters.md
- references/codebase-fit.md

## Judge summary

Strong answer: explicit Impact Read led with blast radius (duplicate money side effect, P0), correct primary routing to reliability-async + api-contracts + language-adapters + codebase-fit, zero generic checklist advice, concrete file:line cites, and an excellent verified proof — I confirmed the tests exist, the duplicate test asserts exactly one charge and one paid order, plants were left intact, and go test -race passes. It also found non-obvious failure modes (provider-side key forwarding for lost responses, reserved order id fence, in-flight 409, decline replay). Held to 3 rather than 4 because two expected behaviors are unaddressed in prose: the DB-transaction-around-network-call hazard and the outbox suggestion for production — both live in references/persistence-migrations.md, which the agent never loaded because the routing table's persistence signals ('SQL, transaction, migration...') don't fire on a payment-endpoint task with an in-memory store.

## Misses

- Never discusses avoiding a DB transaction around the payment provider call. The code trivially avoids it (fixture store has no transactions; charge happens before store.Add), but the production caveats mention only a durable table + unique constraint — the transaction-boundary warning a real port needs is absent
- Never suggests the outbox pattern by name or as the production-grade shape for the write+external-call pairing; the state machine is implemented but not framed as the alternative to a transaction spanning the network call
- Did not load references/persistence-migrations.md, which is exactly where 'Do not hold a DB transaction open across network calls, email, payment...' (line 21) and 'use outbox/inbox/state machine for external side effects' (line 27) live — the two misses above correlate directly with this routing gap

## Changes needed in skill/reference/failure card

- SKILL.md routing table (/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md:93): extend the persistence-migrations row signal list from 'SQL, ORM, Mongo, migration, transaction, index, query performance' to also include 'payment, money movement, DB write paired with an external call in one request' — the literal keyword 'transaction' never appears in a task like this one, so the row never fires
- references/reliability-async.md 'Retry only safe operations' section: add a bullet 'If the side effect pairs a local DB write with an external call (payment, email, queue publish), also read references/persistence-migrations.md — never hold a transaction across the call; use outbox or an explicit state machine' so agents routed here first get the cross-link
- FAILURE_CARDS.md api-idempotency-missing-on-mutation-retry card (line ~99): extend the Safe pattern to 'persist idempotency key with request fingerprint and final response; replay same result for duplicate key; when the mutation also writes local state, state the transaction boundary explicitly and use outbox/state machine — even when the current store has no transactions, say so'

## Tested agent answer (verbatim)

````text
All green: 16 tests pass under `-race`, `go vet` and `gofmt` clean. Final answer below.

---

## Result: `POST /orders/checkout` — idempotent order creation + payment charge

Implemented in the `go-http` fixture, following its existing conventions (flat `main` package, swappable `callX` client transports, `http.Error` plain-text errors, `httptest` table-style tests).

### Impact Read (what drove the design)

- **Side effect that can repeat**: clients retry on network failures, and the endpoint moves money. Without protection, a retry of a request whose *response* was lost duplicates the charge (P0: duplicate money side effect). This is the `api-idempotency-missing-on-mutation-retry` failure pattern.
- **Contract**: new public endpoint with explicit DTOs (no store rows serialized).
- **Deliberately not reused**: `InventoryClient.Reserve` (`inventory.go:35-44`) retries forever with a fixed 1s sleep — an unbounded retry storm. The new `PaymentClient` uses bounded attempts + capped exponential backoff + full jitter instead.
- **Auth/tenant**: the fixture has none; assumed out of scope, noted below.

### Contract

`POST /orders/checkout`, header `Idempotency-Key: <client-generated>` (required, 400 without it), body `{"item": "webcam"}`. The price is derived server-side from `PricingClient` — the client never supplies money fields, so it cannot pick what it pays.

Success `201`: `{"order_id","status":"paid","item","amount_cents","currency","payment_id"}`.

| Situation | Response |
|---|---|
| Duplicate of a completed request (same key + same body) | Recorded response replayed byte-identically; **no second charge, no second order** |
| Same key, different body (fingerprint = SHA-256 of raw body) | `422` |
| Same key while first request still in flight | `409` + `Retry-After` (no race into a second charge) |
| Provider declined (permanent) | `402`, recorded — duplicates replay the decline without contacting the provider |
| Transient provider failure after 3 attempts / pricing down / timeout | `502`/`504`, key released as retryable — client retries with the **same key** |

### Idempotency mechanics (the money-safety core)

1. `idempotencyStore.begin` claims the key and **reserves the order id on first use**; a retry after transient failure reuses it, so one key can never yield two orders (`store.Add` would fail loudly on the duplicate id as a second fence).
2. The same `Idempotency-Key` is forwarded to the provider **on every attempt** (`ChargeRequest.IdempotencyKey`), so a charge that succeeded but whose response was lost is deduplicated provider-side — this is what makes both in-process retries and cross-request client retries safe.
3. Final responses (success *and* decline) are persisted and replayed; transient failures release the key.
4. Charge succeeded but order save failed → key stays retryable; the retry re-presents the same provider key and gets deduplicated instead of double-charging.

Retry policy (`PaymentClient.Charge`): max 3 attempts, base 100ms doubling capped at 1s, full jitter, sleep aborts on context cancellation; only `TransientPaymentError` retries — declines and context errors return immediately. The whole checkout runs under a 10s timeout **derived from `r.Context()`** so a client disconnect cancels downstream work (unlike the fixture's planted `context.Background()` pattern).

Stated assumptions: in-memory idempotency ledger matches the fixture's in-memory store — production needs a durable table with a unique key constraint so the guarantee survives restarts/replicas; no auth in the fixture, so keys are not scoped per principal (production: scope key uniqueness per authenticated client).

### Files changed (all under `/Users/oleg/Desktop/backend-skills/fixtures/go-http/`)

- `payment.go` (new) — `PaymentClient` with bounded/jittered retry, `TransientPaymentError`, `PaymentDeclinedError`, context-aware sleep
- `idempotency.go` (new) — key ledger with in-flight / retryable / completed states, fingerprint check, reserved order id
- `handlers.go` — `handleCheckout`, request/response DTOs, `requestFingerprint`, `finishCheckout`
- `main.go` — server fields `payments`/`idempotency`, `newServer` param, route `POST /orders/checkout`
- `checkout_test.go` (new) — 9 tests incl. duplicate-charges-once, bounded backoff, cross-request retry safety, decline replay, in-flight conflict
- `handlers_test.go` — `newTestServer` wiring only

Note: the fixture was concurrently modified by another session during this task (pricing/shipping fan-out added); my changes were integrated against the final state and the whole suite verified after.

### Proof (final proof contract)

- `go test -race ./...` → `ok example.com/orders-fixture 1.283s` (all 16 tests, including the 7 pre-existing ones, pass)
- Key verifiers inspected individually: `TestCheckoutDuplicateRequestChargesOnce`, `TestCheckoutRetriesTransientFailureWithBoundedBackoff`, `TestCheckoutClientRetryAfterExhaustedAttemptsChargesOnce` (4 provider calls, same key/order id on all, exactly 1 paid order), `TestCheckoutDeclineIsRecordedAndReplayed`, `TestCheckoutConcurrentDuplicateConflicts` — all `--- PASS`
- `go vet ./...` and `gofmt -l .` — clean

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/main.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers_test.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/inventory.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/pricing.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/shipping.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/go.mod
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/internal/store/store.go
````
