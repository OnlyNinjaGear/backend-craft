# Language adapters

Read this after the relevant risk reference. Language rules adapt the safe
pattern to Python, Go, or TypeScript/Node; they do not replace API/security/DB
reasoning.

## Python

### Async cancellation

Use `asyncio.timeout` for time budgets and `TaskGroup` for owned child tasks
when available. Do not create untracked background tasks in request handlers.

Bad signatures:

- `asyncio.create_task(...)` with no owner
- `except Exception: pass`
- swallowing cancellation in broad exception handlers
- `time.sleep()` in async code

Verifier:

- cancellation test
- Ruff rules for broad exceptions and blocking calls where configured

### Exceptions

Catch specific exceptions. Use `logging.exception` or equivalent structured
logging when preserving traceback. Re-raise when the invariant is unknown.

### Types

For new production code, prefer strict typing at boundaries and domain logic.
For legacy code, ratchet strictness per package instead of flipping the whole
repo in one noisy change.

## Go

### HTTP server timeouts

Zero-value `http.Server` timeouts mean no timeout (per `net/http` docs), so
package-level `http.ListenAndServe(addr, handler)` ships a server that slow or
stalled clients can hold open indefinitely.

Bad signatures:

- `http.ListenAndServe(...)` / `http.ListenAndServeTLS(...)` at startup
- `&http.Server{Addr: ..., Handler: ...}` with neither `ReadTimeout` nor
  `ReadHeaderTimeout`

Safe pattern: construct `http.Server` with `ReadHeaderTimeout` at minimum
(handlers then own body deadlines), plus `ReadTimeout`/`WriteTimeout`/
`IdleTimeout` for the workload; pair with `Server.Shutdown` for graceful stop.

Verifier: startup config review or test asserting the fields are non-zero.
Escape hatch: localhost-only dev/debug/pprof listeners and `httptest.Server`.

### Context propagation

Request-scoped work accepts `context.Context` and passes it to DB/HTTP calls.
Call returned cancel functions to release resources.

Bad signatures:

- `context.Background()` inside request path
- goroutine launched without context/lifecycle
- DB call without context variant when one exists

### Goroutines

Use `errgroup.WithContext` or a bounded worker pool for request/job fan-out.
Errors from goroutines must be observable.

Panics: request-scoped supervised goroutines must recover panics and convert
them to errors — a bare WaitGroup goroutine panic kills the process
(errgroup >= v0.9.0 re-panics on the waiting goroutine, where net/http handler
recovery applies). In zero-dependency modules, WaitGroup + explicit error and
panic capture is the sanctioned stdlib fallback to errgroup.

### Errors

Do not ignore errors. Wrap errors when adding useful context and preserve
machine-checkable causes where callers need them.

Verifier:

- `go test ./...`
- `go vet`
- golangci-lint with `errcheck`, `govet`, `gosec`, and context-related linters
  when the project already supports them

## TypeScript and Node

### Boundaries

Use runtime validation at external boundaries. `unknown` before validation,
typed domain objects after validation. Avoid `any` and `as unknown as` in public
paths.

### Async

Every promise is awaited, returned, caught, or intentionally detached with
documented lifecycle. Detached work needs shutdown/error handling.

### Cancellation and timeouts

Use `AbortController`/`AbortSignal` for cancellable operations where supported.
Do not set only outer timers while underlying work continues.

### Event loop

Request handlers must not perform large CPU work or sync file/crypto/compression
operations. Move heavy work to workers/processes or stream it.

Verifier:

- project-local `typecheck`
- eslint/typescript-eslint `no-floating-promises`, `no-explicit-any`
- event-loop/load test for hot paths when CPU work is introduced
