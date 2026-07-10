# Reliability, async, and side effects

Read this when touching retries, timeouts, cancellation, external APIs, queues,
workers, cron jobs, webhooks, background tasks, graceful shutdown, rate limits,
or overload behavior.

## Reliability read

Identify:

- side effects and whether they are idempotent
- retry policy and retryable errors
- timeout/deadline owner
- cancellation propagation path
- downstream capacity/rate limit
- duplicate delivery and partial failure behavior

## Non-negotiables

### Retry only safe operations

Before adding retries, prove the operation is idempotent or protected by an
idempotency key/dedupe mechanism.

Safe retry shape:

- bounded attempts
- max elapsed time
- exponential backoff with jitter
- respect `Retry-After`
- no retry for validation/auth/permanent errors

If the side effect pairs a local DB write with an external call (payment,
email, queue publish), also read `persistence-migrations.md`: never hold a
transaction across the call; use an outbox or explicit state machine. State
the transaction boundary even when the current store has no transactions.

### Timeouts must cancel downstream work

An outer timeout is incomplete if DB queries, HTTP requests, goroutines,
asyncio tasks, or promises continue running.

Safe pattern:

- Go: pass `context.Context` into DB/HTTP/downstream calls
- Python: use `asyncio.timeout`/TaskGroup and re-raise cancellation
- Node: pass `AbortSignal` into fetch/timers/client calls where supported

### Queue consumers assume at-least-once delivery

Exactly-once is not the default. Consumers must tolerate duplicate messages.

Safe pattern:

- idempotency key, inbox/dedupe table, or idempotent state transition
- retry-safe side effects
- dead-letter strategy for poison messages

Cross-links that fire even when the task reads as pure reliability work:

- worker sends user-facing communications (email/SMS/push) -> it touches PII
  and tenant boundaries; also load `auth-tenancy-security.md`
- background work persists data (new table, outbox, event log) -> also load
  `persistence-migrations.md` before writing the migration

### Concurrency is bounded

Do not spawn work per item over unbounded input. Bound concurrency by downstream
capacity and pool sizes.

Bad signatures:

- `Promise.all(items.map(...))` over arbitrary collection
- `asyncio.gather(*tasks)` over arbitrary collection
- `for ... go func()` without worker limit

## Common failure cards

- `retry-without-jitter-or-cap`
- `circuit-breaker-missing-on-fragile-dependency`
- `queue-consumer-not-idempotent`
- `worker-unbounded-concurrency`
- `timeout-without-cancellation-propagation`
- `event-loop-blocking`
- `go-goroutine-without-lifecycle`
- `python-async-cancel-swallowed`
- `ts-floating-promise`

## Verifiers

- duplicate delivery test
- retry count and timing test
- downstream failure test with bounded latency
- cancellation test — for owned worker pools this is a dedicated test asserting
  a cancelled task exits (`task.cancelled()` is true / `stop()` completes
  within the drain timeout), not an implicit side effect of lifespan teardown
- graceful shutdown test
- max concurrency test
- event-loop delay or benchmark for Node hot path
- bulk export/streaming path: a concrete proof of bounded work (row-cap test or
  streamed-response assertion), not a comment claiming the dataset is small
