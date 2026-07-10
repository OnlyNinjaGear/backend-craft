# forward-test 104: payment-idempotency (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/go-http
Score: 4/4 (round 1: 3/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. Cited specific test names with inspected outcomes (duplicate-retry => 1 charge/1 order/identical body; transient-failure => 3 bounded attempts then reuse of same order; decline replay; 409 in-flight), plus race detector, vet, gofmt. Independently reproduced: go vet clean, go test -count=1 pass, go test -race pass; assertions in checkout_test.go match the claims (charges.Load() != 1 fails the test). Files-changed list matches the working tree.

## Prompt

```text
Add an endpoint that creates an order and calls a payment provider. Clients may retry on network failures.
```

## Round-2 focus verdict

Transaction-boundary focus: SATISFIED. persistence-migrations.md is in Files read (routing row hit). The answer explicitly states no transaction is held across the payment provider call, and checkout.go:99-101 documents it in code. The production shape is named as a state machine (pending_payment -> charge -> paid/payment_failed) with a documented reconciliation sweep for crashed in-flight records and short-transaction key-claim noted for a real DB. 'Outbox' itself is never named, but the reference offers 'outbox/inbox/state machine' as alternatives and state machine is the apt one for a synchronous checkout; treating the disjunction as satisfied.

## References loaded

- SKILL.md
- references/reliability-async.md
- references/persistence-migrations.md
- references/api-contracts.md
- references/language-adapters.md
- references/testing-verification.md

## Judge summary

Round 2 closes the round-1 miss: persistence-migrations.md was loaded (routing fix worked), the no-transaction-across-the-provider-call boundary is explicitly discussed in the answer and in checkout.go code comments, and the state-machine production shape (pending_payment -> paid/payment_failed with reconciliation sweep) is named. All proof claims independently reproduced: go vet clean, full suite and -race pass, duplicate-retry test asserts exactly one charge and one order. Idempotency store persists fingerprint and replays stored responses; concurrent-duplicate 409, fingerprint-mismatch 422, decline replay, and bounded jittered provider retries all implemented and tested. Non-obvious failure modes (ambiguous timeout window closed by forwarding the key to the provider, order reuse on retry, tenant-scoped keys flagged) plus verified proof merit a 4.

## Misses

- The word 'outbox' never appears in the answer or code — the agent named only the state-machine shape (defensible for a synchronous checkout, and the reference phrases it as 'outbox/inbox/state machine', so this is an alternative satisfied, not a hard miss)
- No explicit Impact Read section shown in the final answer (the blast-radius analysis is clearly embedded in the design, but the workflow step is not surfaced)

## Changes needed

- none

## Tested agent answer (verbatim)

````text
All verifiers pass, including the race detector. Work is complete.

## What was built

New endpoint: **`POST /orders/checkout`** — creates an order and charges a payment provider, safe under client retries.

### Contract

Request: `Idempotency-Key` header (required, ≤128 chars) + JSON body `{"item": string, "amount_cents": int > 0 (≤10,000,000), "currency": "USD" (3-letter ISO shape)}`. Money is integer minor units, never floats.

Responses (JSON error contract with stable machine-readable codes, since clients must decide retryability):
- `201` — explicit DTO `{order_id, status, item, amount_cents, currency, payment_id}` (never the persistence model)
- `400` missing/oversized key, invalid JSON, validation failure; `413` body over 64 KB
- `409` + `Retry-After` — same key currently in flight (concurrent duplicate)
- `422` — key reused with a different body (fingerprint mismatch)
- `402 payment_declined` — permanent; stored and **replayed** on retry, never re-charged
- `502 payment_unavailable` / `504 payment_timeout` — transient; client retries with the **same key**
- Replays carry `Idempotency-Replayed: true` and byte-identical bodies

### Reliability design (the "clients may retry" core)

1. **Idempotency record claimed before any side effect** (`internal/store/idempotency.go`, pretend `idempotency_keys` table): key + SHA-256 body fingerprint + state (`in_flight → retryable | completed`) + bound order id + final response. Duplicate outcomes: replay / 409 / 422.
2. **Same idempotency key forwarded to the provider**, so a retry after an ambiguous network failure (timeout mid-charge) cannot double-charge — provider-side dedupe covers the unknown-outcome window.
3. **No transaction across the network call** — state machine instead: order written `pending_payment` → charge → `paid`/`payment_failed`. A retry after a transient failure **reuses the bound order** (no duplicate rows); crash-recovery via reconciliation sweep is documented at the record store.
4. **Bounded provider retries** (`payments.go`): 3 attempts max, exponential backoff with full jitter (100 ms base, 1 s cap), transient errors only (declines return immediately), handler-owned 5 s deadline, context cancellation aborts backoff sleeps. Replaces nothing existing — deliberately does *not* copy `InventoryClient.Reserve`'s infinite retry loop.

### Files changed (all absolute, under the project root)

- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/checkout.go` — new: handler, DTOs, validation, error contract
- `.../004-go-http/payments.go` — new: `PaymentClient` with bounded jittered retry, `ErrPaymentDeclined`/`ErrProviderUnavailable`
- `.../004-go-http/internal/store/idempotency.go` — new: idempotency-key store (`Begin/BindOrder/Complete/Retryable`)
- `.../004-go-http/internal/store/store.go` — added `Get(id)` and `UpdateStatus(id, status)`
- `.../004-go-http/main.go` — route registration; `server` gains `payments`/`idem`; `newServer(st, inv, pay, idem)`
- `.../004-go-http/checkout_test.go`, `.../004-go-http/payments_test.go` — new tests
- `.../004-go-http/handlers_test.go` — helper updated for new constructor signature

### Proof (output inspected)

- `go test -v -run 'Checkout|Charge' ./...` — 12 new tests PASS, covering the proof matrix: happy path; **duplicate-request test** (retry ⇒ 1 charge, 1 order, identical replayed body); 422 mismatch; missing key; 6 validation cases; **transient-failure test** (exactly 3 bounded attempts ⇒ 502, then retry succeeds reusing the same order — 4 total attempts, zero leftover `pending_payment` rows); **decline-terminal test** (1 attempt, replayed 402); 409 in-flight with `Retry-After`; backoff delays within jitter caps; attempts exhausted at `maxAttempts`; no retry on decline; prompt return on context cancel.
- `go test -count=1 ./...` — full suite ok (pre-existing 5 tests unaffected).
- `go test -race -count=1 ./...` — ok.
- `gofmt -l` clean, `go vet ./...` clean.

### Assumptions and residual risks

- No auth/tenancy exists in this fixture; in production the idempotency key must be scoped per principal (`(tenant_id, key)`), or one tenant could replay another's responses.
- The in-memory store has no transactions; in a real DB, `Begin` is `INSERT ... ON CONFLICT` and order-create + key-claim share one short transaction (documented in code). In-memory idempotency records also don't survive restarts — a real deployment needs them in the DB with TTL cleanup.
- Pre-existing fixture flaws left untouched (out of scope): SQL string interpolation in `handleListOrders`, infinite retry loop in `InventoryClient.Reserve`, fire-and-forget email goroutine, non-idempotent `POST /orders`. These are the next highest-value hardening targets.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/main.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/handlers.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/inventory.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/internal/store/store.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/handlers_test.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/004-go-http/go.mod
````
