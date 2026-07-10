# forward-test 009: go-parallel-fanout

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/go-http
Score: 4/4
Generic advice: False
Verifier quality (judge): Excellent. TestGetOrderFansOutConcurrently uses a 3-party barrier so a sequential implementation deterministically fails (not a timing heuristic); TestGetOrderDownstreamFailureCancelsSiblings asserts the sibling context was actually cancelled after the first failure; TestGetOrderByID pins the old fields and the new ones (contract check). All run under go test -race -count=1, independently re-executed by the grader and passing. Matches the reliability-async verifier list (cancellation test, downstream failure test with bounded latency) precisely.

## Prompt

```text
In this Go service, parallelize calls to three downstream services in the request handler.
```

## References loaded (from agent's 'Files read')

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md

## Judge summary

Verified all agent claims by rerunning go vet and go test -race -count=1 (pass, including both new concurrency verifiers). The agent hit all four expected behaviors: request-context-derived bounded timeout, errgroup-equivalent fan-out with justified stdlib substitution, first-failure sibling cancellation with observable joined errors, and no naked goroutines. It found the non-obvious failure mode — the planted timeout-without-cancellation-propagation flaw sat at the exact call site being parallelized — fixed it as part of the change, and left the other four plants untouched with precise file:line citations. The verifier is exemplary: a deterministic 3-party barrier test that fails under a sequential implementation, and a sibling-cancellation test asserting the context was actually cancelled. Only deductions worth noting are a missed api-contracts.md routing row for the additive response-DTO change (mitigated by a contract assertion in tests) and small reporting inaccuracies about the constructor signature and file newness; neither undermines safety or proof, so this meets the score-4 bar.

## Misses

- did not load references/api-contracts.md despite adding two fields to the public GET /orders/{id} response, which matches the routing row 'DTO, public response' (partially mitigated by the backward-compat reasoning and the contract assertion added to TestGetOrderByID)
- minor reporting inaccuracies: claims newServer(st, inv, pr, sh) but the actual signature has a fifth PaymentClient param, and labels pricing.go '(new)' although pre-existing checkout code already references s.pricing

## Changes needed in skill/reference/failure card

- In SKILL.md's reference routing section, add a note that a single change often matches multiple rows and all matched rows must be loaded — e.g. a concurrency change that also alters a response body triggers both reliability-async.md and api-contracts.md; alternatively add 'response field added/removed' as an explicit signal in the api-contracts row so additive changes are not skipped as 'backward compatible'
- In the final proof contract, require the 'files changed' list to be re-verified against the working tree before reporting (signatures and new-vs-modified status), to prevent stale claims like a wrong constructor arity

## Tested agent answer (verbatim)

````text
All green: `go vet` clean, full suite passes with `-race` and `-count=1`, including the two new concurrency verifiers.

## Result

**Task**: parallelize calls to three downstream services in the request handler of the Go service at `/Users/oleg/Desktop/backend-skills/fixtures/go-http`.

**Stated assumption**: the fixture had only one downstream service (`InventoryClient`). To have three, I added two more pretend downstream clients (`PricingClient`, `ShippingClient`) built on the exact same pattern as `InventoryClient` (swappable transport funcs for test fakes), and made `GET /orders/{id}` (`handleGetOrder`) the fan-out handler, since it already made a downstream call. The response gains two additive JSON fields (`unit_price_cents`, `shipping_eta_days`) — backward compatible; existing fields unchanged.

### Design (per backend-craft reliability-async + Go adapter rules)

- **Fan-out**: `sync.WaitGroup.Go` (stdlib, Go ≥1.25; module is `go 1.26`) launches exactly 3 goroutines — bounded by construction, no unbounded per-item spawning. Chose stdlib over `golang.org/x/sync/errgroup` deliberately: the module has zero dependencies and adding one could break hermetic/offline builds; the manual pattern reproduces errgroup semantics (first error cancels siblings).
- **Cancellation propagation**: the shared 2s downstream budget is now derived from `r.Context()` instead of `context.Background()` — this also fixes the planted `timeout-without-cancellation-propagation` bug that lived at the exact call site being parallelized (skill non-negotiable: timeouts must cancel downstream work; client disconnect now cancels all three calls).
- **First-failure cancellation**: each goroutine calls `cancel()` on error, so a failing service doesn't let siblings run out the clock.
- **Errors observable**: per-call error vars joined with `errors.Join`, logged, mapped to `502 Bad Gateway` (consistent with the handler's existing downstream-failure status).
- **No data races**: results written in separate goroutines, read only after `wg.Wait()` (happens-before via WaitGroup); confirmed by `-race`.

### Files changed

- `/Users/oleg/Desktop/backend-skills/fixtures/go-http/pricing.go` (new) — `PricingClient.GetPrice(ctx, item) (int, error)`
- `/Users/oleg/Desktop/backend-skills/fixtures/go-http/shipping.go` (new) — `ShippingClient.EstimateDays(ctx, item) (int, error)`
- `/Users/oleg/Desktop/backend-skills/fixtures/go-http/main.go` — server struct + `newServer(st, inv, pr, sh)` wiring
- `/Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers.go` — parallel fan-out in `handleGetOrder`
- `/Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers_test.go` — updated constructor, extended `TestGetOrderByID`, two new verifiers

### Verification (final proof contract)

- `go vet ./...` — clean.
- `go test -race -count=1 ./...` — **PASS**, 7/7 tests, including:
  - `TestGetOrderFansOutConcurrently` — deterministic proof of parallelism: each fake blocks on a 3-party barrier until all three calls are in flight; a sequential implementation fails the test (barrier timeout → 502).
  - `TestGetOrderDownstreamFailureCancelsSiblings` — pricing fails immediately; the shipping fake returns only when its context is cancelled; asserts 502 and that the sibling context was actually cancelled.
  - `TestGetOrderByID` — asserts old fields preserved and new fields present (contract check).

### Out-of-scope findings (observed, deliberately not changed)

Other planted issues remain and were left untouched to keep the diff scoped: SQL string concatenation in `handleListOrders` (handlers.go:23, P0 injection), ignored audit-log error and lifecycle-less email goroutine in `handleCreateOrder` (handlers.go:60–65), and the uncapped no-jitter retry loop in `InventoryClient.Reserve` (inventory.go:36–44). Note `Reserve` is also called in `handleCreateOrder` without a context — same fix shape would apply there if requested.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/main.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/inventory.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/handlers_test.go
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/go.mod
- /Users/oleg/Desktop/backend-skills/fixtures/go-http/internal/store/store.go
````
