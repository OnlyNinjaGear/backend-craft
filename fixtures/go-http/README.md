# go-http — intentionally flawed orders API fixture

## Purpose

Forward-test fixture for the backend-craft code-review skill and for Semgrep
checker rules. It is a tiny, runnable orders API (Go stdlib only, zero
external dependencies) with **exactly 6 planted production-safety failures**,
each mapped to a failure card in `../../FAILURE_CARDS.md` and marked in code
with a `// PLANTED: <card-id>` comment. It also contains deliberately clean
contrast code so checker false-positive rates can be measured.

The flaws are production-safety flaws, not compile errors: `go vet` is clean
and the happy-path tests pass. **Do not fix the planted flaws** — the fixture
exists to be reviewed, not repaired.

## How to run tests

```sh
cd /Users/oleg/Desktop/backend-skills/fixtures/go-http && go vet ./... && go test ./...
```

To run the server (optional): `go run .` (listens on `:8080`).

## Expected failures

| card id | file:line area | description |
|---|---|---|
| sql-string-concat | handlers.go:22-24 | GET /orders builds SQL with `fmt.Sprintf(... '%s' ...)` from the raw `status` query param and passes it to `store.Query` |
| go-ignored-error | handlers.go:59-60 | POST /orders discards the audit-log write error with `_ = s.store.Exec(...)` |
| go-goroutine-without-lifecycle | handlers.go:62-65 | POST /orders fires a naked `go func(){ sendConfirmationEmail(order) }()` — no context, no error handling, no panic recovery, no wait |
| timeout-without-cancellation-propagation | handlers.go:86-89 | GET /orders/{id} calls the inventory client with a timeout derived from `context.Background()` instead of `r.Context()`, so client disconnect never cancels the downstream call |
| retry-without-jitter-or-cap | inventory.go:36-46 | `InventoryClient.Reserve` (a mutating call) retries in a loop bounded only by success, with fixed `time.Sleep(1 * time.Second)`, no attempt cap, no jitter |
| go-http-server-no-timeouts | ops.go:20-43 | ops listener is a bare `&http.Server{Addr, Handler}` (all timeout fields zero = no timeout) and the debug listener is package-level `http.ListenAndServe(":6060", nil)`; both bind all interfaces, so the localhost escape hatch does not apply (two plant sites, one card) |

## Clean contrast code (should NOT be flagged)

- `handlers.go` `handleSearchOrders` (GET /orders/search): constant
  parameterized query (`WHERE status = ?`) via `store.QueryContext` with
  `r.Context()` propagated, every error checked and mapped to a status code.
- `handlers.go` `handleGetOrder` store lookup: parameterized
  `QueryContext(r.Context(), "... WHERE id = ?", id)` (the plant in that
  handler is only the inventory call below it).
- `handlers.go` `writeJSON`: JSON encode errors are checked and logged.
- `handlers.go` `handleCreateOrder`: `inventory.Reserve` and `store.Add`
  errors are handled correctly (the plants there are the audit `Exec` and the
  naked goroutine).
- `main.go` primary server: `&http.Server{}` with `ReadHeaderTimeout`,
  `ReadTimeout`, and `WriteTimeout` set — the clean-pass regression for the
  server-timeout rules.
- `main.go` `go startOps()` / `go startDebug()`: process-lifetime goroutines
  registered at startup — the goroutine card's escape hatch; the
  handler-scoped goroutine rule must not fire on them.

## Layout

- `main.go` — server wiring, routes, seed data
- `ops.go` — ops/debug listeners (the server-timeout plant, two sites)
- `handlers.go` — HTTP handlers (4 plants)
- `inventory.go` — pretend downstream inventory client (retry plant); tests
  inject a fake that succeeds on the first attempt
- `internal/store/store.go` — in-memory fake SQL store exposing
  `Query(q)`, `Exec(q)`, and `QueryContext(ctx, q, args...)`; it parses
  nothing and matches on substrings. The pretend `orders` table is assumed
  large in production (10M+ rows).
- `handlers_test.go` — 5 happy-path httptest tests (all must pass)
