# forward-test 109: go-parallel-fanout (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/go-http
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Excellent — behavioral, failure-sensitive tests rather than happy-path assertions: TestCreateOrderAuditAndEmailRunConcurrently blocks the email until the audit write is visible so it fails by timeout if the calls are serialized; TestCreateOrderEmailFailureStillCreatesOrder exercises the SMTP-down path; TestCreateOrderEmailCompletesBeforeResponse proves supervision the old detached goroutine could not; all run under -race with vet, and I reproduced every result independently on the working tree.

## Prompt

```text

```

## Round-2 focus verdict

FOCUS 1 (api-contracts.md routing): PASS — I diffed the working tree; the response is still 201 + the identical order JSON DTO, so no api-contracts row matched and not loading it is correct per SKILL.md's own routing example ("a concurrency change that also adds a response field triggers both"); the agent explicitly stated the contract was preserved. FOCUS 2 (files-changed vs working tree): PASS — diff confirms handlers.go/main.go/handlers_test.go changed exactly as claimed (including the func(ctx context.Context, o store.Order) error signature and the 3 named new tests), inventory.go and internal/store untouched, and the answer states the list was verified against the working tree as the proof contract now requires; I reproduced go vet clean and go test -race 8/8 PASS.

## References loaded

- SKILL.md (via skill invocation)
- references/reliability-async.md
- references/testing-verification.md
- references/language-adapters.md

## Judge summary

Near-exemplary round-2 run. The agent refused the naive reading of "parallelize three calls," proved via dependency analysis that only audit||email are safe to run concurrently (Reserve->Add parallelization would be a P0), and shipped a supervised, timeout-bounded, WithoutCancel-based implementation with a genuinely discriminating concurrency test suite that I reproduced (8/8 PASS under -race, vet clean). Both ROUND-2 FOCUS items verified against ground truth: response body confirmed unchanged so api-contracts.md was correctly not matched, and the files-changed list matches the working tree exactly down to the new sendConfirmationEmail signature. Only nits: no panic recovery in the supervised goroutines (part of the original flaw card) and an unacknowledged deviation from the errgroup adapter rule, both worth small reference edits rather than score deductions.

## Misses

- No panic recovery in the two supervised goroutines: a panic in s.sendEmail or store.Exec now crashes the whole process (unrecovered goroutine panics are fatal in Go); the planted go-goroutine-without-lifecycle card explicitly listed 'no panic recovery' as part of the flaw
- Used sync.WaitGroup instead of the language-adapters.md prescription 'errgroup.WithContext ... for request/job fan-out' — the zero-dependency justification is sound and errors remain observable, but the deviation from the adapter rule was not explicitly acknowledged

## Changes needed

- language-adapters.md Goroutines section: add a panic rule — request-scoped supervised goroutines must recover panics and convert them to errors (or use errgroup >= v0.9.0, whose Wait re-panics on the waiting goroutine where net/http handler recovery applies); a bare WaitGroup goroutine panic kills the process
- language-adapters.md: state the sanctioned stdlib fallback explicitly (WaitGroup + error capture is acceptable in zero-dependency modules) so agents deviating from errgroup cite the rule instead of improvising the justification

## Tested agent answer (verbatim)

````text
All green: `go build`, `go vet` clean, and `go test -race -count=1` passes 8/8 tests (5 pre-existing + 3 new), no data races.

## Result

**Assumption (stated, not asked):** The service has exactly three downstream dependencies — the inventory service, the database, and the email/SMTP service — and the only handler that calls all three is `handleCreateOrder` (`POST /orders`). That handler is the parallelization target. No handler in the fixture has three *mutually independent* calls: in `handleGetOrder` the inventory check needs `item` from the DB row (hard data dependency, inherently sequential), and in `handleCreateOrder` two of the calls are causally ordered.

**Design — parallelize only what the dependency graph allows:**

- `inventory.Reserve → store.Add` stays **sequential**. Reserving stock gates order acceptance; running these in parallel could persist orders with no reservation (oversell / compensation logic) — a P0, so it is deliberately excluded and documented in a comment.
- `audit_log` insert **∥** confirmation email now run **concurrently** after the order is persisted: both depend only on the persisted order, not on each other. Latency for the post-persist phase is `max(audit, email)` instead of `audit + then a detached email`.
- Structured concurrency with `sync.WaitGroup` (stdlib only — the module has zero deps), both awaited before responding. This also fixes the pre-existing `go-goroutine-without-lifecycle` flaw: the old fire-and-forget email goroutine discarded its error and could outlive the request/process.
- Context: `context.WithTimeout(context.WithoutCancel(r.Context()), 5s)` — client disconnect after persist can no longer suppress the audit trail or email, but a stuck downstream can't hold the handler open; `sendConfirmationEmail` now accepts and honors `ctx`.
- Contract preserved: still `201` + order JSON; audit/email failures are logged, not returned (the order is already persisted — a 5xx would invite client retries that create duplicate orders). The previously discarded `store.Exec` error is now logged.
- Testability seam: `server.sendEmail` field (defaults to `sendConfirmationEmail`), mirroring the existing `InventoryClient` swappable-transport convention.

**Files changed (verified against working tree):**
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/handlers.go` — parallel phase in `handleCreateOrder`; `sendConfirmationEmail` signature now `func(ctx context.Context, o store.Order) error`
- `.../009-go-http/main.go` — `server.sendEmail` field + default wiring in `newServer`
- `.../009-go-http/handlers_test.go` — 3 new tests

**Proof (skill final-proof contract):**
- `go test -race -count=1 ./...` → `ok example.com/orders-fixture`, 8/8 PASS, including:
  - `TestCreateOrderAuditAndEmailRunConcurrently` — injected email sender blocks until the audit insert is visible in the store; passes only if the email call is in flight while the audit write lands (fails by 2s timeout if email is serialized before audit).
  - `TestCreateOrderEmailFailureStillCreatesOrder` — failing-path: SMTP down → still 201 and audit row written.
  - `TestCreateOrderEmailCompletesBeforeResponse` — supervision: email attempt finishes before the handler responds (impossible to guarantee with the old detached goroutine).
  - Pre-existing `TestCreateOrderWritesAuditLog` still passes → audit-before-response behavior preserved.
- `go vet ./...` clean.

**Adjacent findings noticed but intentionally not touched (out of the requested scope):**
- P0: SQL injection via string-formatted query in `handlers.go:22` (`handleListOrders`); the safe counterpart `handleSearchOrders` already exists.
- P1: unbounded retry loop with no backoff cap or context in `inventory.go` `Reserve` (retry storm / handler hangs forever if inventory is down).
- P2: `context.Background()` instead of `r.Context()` for the inventory check in `handleGetOrder` (work continues after client disconnect).
- P2: true fire-and-forget email semantics, if ever required, should move to an outbox/queue rather than a detached goroutine.

**Files read**
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/handlers.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/main.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/inventory.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/handlers_test.go
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/go.mod
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/009-go-http/internal/store/store.go
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
````
