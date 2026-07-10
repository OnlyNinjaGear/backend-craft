# backend-craft failure cards

Failure cards are the unit of knowledge for this package. They are not generic
best practices. Each card names a situation where an agent commonly writes code
that looks plausible and fails under production conditions.

Status values:

- `draft`: plausible and source-backed, not yet observed in this project
- `observed`: seen once in a real project/task
- `production-tested`: repeated or forward-tested; suitable for hard rule
- `retired`: no longer useful or too noisy

## Card template

```md
## card-id

Status:
Triggered by:
Model failure:
Blast radius:
Detect:
Safe pattern:
Verifier:
Escape hatch:
Sources:
```

---

## api-bola-id-swap

Status: production-tested (forward-test 003, 2026-07-10)
Triggered by: adding `GET /resources/{id}`, `PATCH /resources/{id}`, admin/user scoped endpoints.
Model failure: checks authentication but fetches by raw id without verifying that the caller may access that object.
Blast radius: cross-tenant data exposure or mutation.
Detect: route has path id plus DB lookup by id, but no tenant/user/role predicate or ownership authorization call.
Safe pattern: authorize at object boundary: query by `(id, tenant_id)` or call policy with loaded resource before returning/mutating.
Verifier: test user A cannot read/update/delete user B's resource, including guessed ids.
Escape hatch: public resources with explicit public-read policy.
Sources: OWASP API1:2023 Broken Object Level Authorization, OWASP Authorization Cheat Sheet.

## api-bopla-property-leak

Status: production-tested (forward-test 011, 2026-07-10)
Triggered by: serializing ORM/document objects directly in API responses.
Model failure: returns every field from DB model, including internal or unauthorized properties.
Blast radius: PII leakage, privilege escalation through writable fields, contract drift.
Detect: response uses `model.__dict__`, ORM entity, spread object, `SELECT *`, or schema inferred from persistence model.
Safe pattern: explicit response DTO/schema per endpoint; sensitive fields opt-in only.
Verifier: response contract test asserts forbidden fields are absent.
Escape hatch: internal admin endpoint with explicit role gate and documented response schema.
Sources: OWASP API3:2023 Broken Object Property Level Authorization, OpenAPI 3.1.

## api-mass-assignment

Status: production-tested (forward-test 002, 2026-07-10)
Triggered by: create/update handlers mapping request body directly into model update.
Model failure: `update(data)`, `Object.assign(entity, body)`, Pydantic/DTO accepted fields reused as persistence update.
Blast radius: user sets `role`, `tenant_id`, `is_admin`, balance/status fields.
Detect: request body is passed wholesale to DB/ORM update without allowlist.
Safe pattern: command DTO with explicit allowed fields; server-owned fields assigned server-side only.
Verifier: test forbidden writable fields are ignored or rejected.
Escape hatch: trusted internal migration/admin scripts outside HTTP boundary.
Sources: OWASP API3:2023, ASVS access control requirements.

## api-pagination-late

Status: draft
Triggered by: list endpoint returning a collection.
Model failure: returns unbounded arrays and plans to add pagination later.
Blast radius: compatibility break when pagination is added; memory/latency/resource exhaustion.
Detect: `GET /items` returns list without `limit/page_size/cursor` and no max cap.
Safe pattern: pagination from first release; cursor preferred for mutable large collections.
Verifier: contract includes pagination parameters and response tokens; tests cap max page size.
Escape hatch: tiny static enumerations with explicit bounded cardinality.
Sources: AIP-158 Pagination, OWASP API4:2023 Unrestricted Resource Consumption.

## api-error-contract-drift

Status: draft
Triggered by: adding or changing error handling.
Model failure: returns ad hoc errors per handler (`{"error": "..."} vs {"message": ...}`), leaks stack traces, or changes status semantics.
Blast radius: clients break; sensitive internals leak; monitoring loses signal.
Detect: handlers construct error bodies directly instead of shared error mapper.
Safe pattern: one error schema with code, message, request id, optional details; no stack traces to clients.
Verifier: contract tests for representative 4xx/5xx paths.
Escape hatch: intentionally different upstream compatibility layer, documented in OpenAPI.
Sources: OpenAPI 3.1, OWASP REST Security Cheat Sheet.

## api-idempotency-missing-on-mutation-retry

Status: production-tested (forward-test 004, 2026-07-10)
Triggered by: POST/PATCH/DELETE with payment/order/email/webhook side effects or client retry guidance.
Model failure: adds retry or timeout handling without idempotency key/deduplication.
Blast radius: duplicate charge/order/email/job.
Detect: mutating endpoint performs side effect but has no idempotency key, unique operation id, or dedupe table.
Safe pattern: persist idempotency key with request fingerprint and final response; replay same result for duplicate key. When the mutation also writes local state, state the transaction boundary explicitly and use outbox/state machine — even when the current store has no transactions, say so.
Verifier: duplicate request with same key produces one side effect and same response.
Escape hatch: naturally idempotent PUT to a complete resource state with no external side effects.
Sources: Stripe idempotent requests, Stripe idempotency article, AWS Reliability Pillar.

## authz-handler-only

Status: draft
Triggered by: adding service/repository methods used by multiple routes.
Model failure: authorization checked only in one handler while shared service method remains unsafe for other callers.
Blast radius: future endpoint bypasses policy accidentally.
Detect: service accepts user id/resource id but does not encode policy or require authorized principal/context.
Safe pattern: policy at use-case boundary; repository receives scoped predicates; unsafe lower-level methods named/internal.
Verifier: tests call all public use cases with forbidden principal.
Escape hatch: private pure data access function not reachable from request/job boundary.
Sources: OWASP Authorization Cheat Sheet, ASVS access control.

## tenant-filter-forgotten

Status: production-tested (forward-test 003, 2026-07-10)
Triggered by: multi-tenant project, list/search/report/export endpoints.
Model failure: one query lacks `tenant_id` predicate or uses tenant from request body instead of authenticated context.
Blast radius: cross-tenant reads/writes, regulatory incident.
Detect: DB query on tenant-owned table without tenant predicate; tenant id accepted from client.
Safe pattern: tenant scope comes from auth/session; repository helpers require tenant scope.
Verifier: seeded two-tenant integration test proves no leakage on list, get, update, export.
Escape hatch: platform-level global admin endpoint with explicit role and audit log.
Sources: OWASP API1:2023, OWASP Authorization Cheat Sheet.

## pii-logged

Status: draft
Triggered by: adding request/response logging, exception logging, webhook debugging.
Model failure: logs full body, tokens, passwords, emails, payment details, auth headers.
Blast radius: privacy incident; secrets copied into log storage and support tooling.
Detect: logger receives raw request body, headers, exception context with secret-bearing fields.
Safe pattern: structured allowlist logs; redact sensitive keys; include correlation id, not payload dump.
Verifier: test logger/redactor removes known sensitive fields.
Escape hatch: temporary local-only debugging with no committed code and no shared log sink.
Sources: OWASP Logging Cheat Sheet, OWASP API Security.

## ssrf-url-fetch

Status: draft
Triggered by: webhook fetcher, image importer, URL preview, callback validation.
Model failure: fetches user-controlled URL without scheme/host/IP restrictions and redirect policy.
Blast radius: internal metadata/service access, data exfiltration.
Detect: HTTP client consumes URL from request/db/user config.
Safe pattern: allowlist schemes and hosts, block private/link-local ranges after DNS resolution, limit redirects, timeout and size cap.
Verifier: tests reject localhost, private IPs, link-local metadata IPs, DNS rebinding fixture if possible.
Escape hatch: internal admin-only tool running in isolated network with explicit allowlist.
Sources: OWASP API7:2023 SSRF, OWASP SSRF Prevention Cheat Sheet.

## secret-in-config-or-log

Status: draft
Triggered by: adding config examples, logs, errors, seed data.
Model failure: commits real-looking secrets or logs environment variable values.
Blast radius: credential leakage and false confidence in secret hygiene.
Detect: API keys/tokens/passwords in source, fixtures, `.env`, logs, docs.
Safe pattern: placeholders only; load secrets from env/secret manager; never log secret values.
Verifier: secret scan plus review of config output.
Escape hatch: deterministic fake test keys clearly marked and rejected by production providers.
Sources: OWASP ASVS, Node security best practices.

## sql-string-concat

Status: production-tested (forward-test 002, 2026-07-10)
Triggered by: building filters/search/order clauses.
Model failure: concatenates request values into SQL string or f-string/template literal.
Blast radius: SQL injection or broken query semantics.
Detect: SQL string contains interpolated user/request values.
Safe pattern: parameterized values; allowlisted identifiers for dynamic sort/filter fields.
Verifier: injection payload test and linter/Semgrep rule.
Escape hatch: static SQL fragments selected from constant allowlist.
Sources: CWE-89, OWASP ASVS, PostgreSQL docs.

## db-transaction-around-network-call

Status: production-tested (forward-test 104, 2026-07-10)
Triggered by: endpoint creates DB row and calls payment/email/external API.
Model failure: opens DB transaction, then performs network call inside it.
Blast radius: long-held locks, deadlocks, duplicate side effects on retry, poor throughput.
Detect: transaction scope includes HTTP/email/payment/queue publish call.
Safe pattern: keep DB transaction short; use outbox/inbox or state machine for external side effects.
Verifier: integration test proves transaction commits quickly and outbox worker handles external call idempotently.
Escape hatch: rare local RPC guaranteed bounded and necessary for serializable invariant; document timeout and lock impact.
Sources: PostgreSQL explicit locking, AWS Reliability Pillar.

## migration-non-online-ddl

Status: production-tested (forward-test 005, 2026-07-10)
Triggered by: altering large/hot table.
Model failure: writes direct blocking DDL or backfills all rows in one transaction.
Blast radius: table lock, outage, replication lag.
Detect: migration contains `ALTER TABLE` on hot table, full-table update, index creation without online/concurrent strategy.
Safe pattern: expand/contract migration, concurrent index where supported, batched backfill, app compatibility window.
Verifier: migration dry run on production-like data or explicit lock analysis.
Escape hatch: tiny table with measured row count and maintenance window.
Sources: PostgreSQL ALTER TABLE, PostgreSQL explicit locking.

## migration-no-rollback-plan

Status: draft
Triggered by: schema/data migration in production path.
Model failure: only writes `up`; no rollback, no forward-fix note, no backup/restore assumptions.
Blast radius: failed deploy leaves app and DB incompatible.
Detect: migration lacks `down` or irreversible annotation.
Safe pattern: reversible migration, or explicit irreversible-with-forward-fix note and deployment sequence.
Verifier: run up/down on throwaway DB or document irreversible proof.
Escape hatch: destructive legal/data-retention migration with signoff.
Sources: deployment safety practice, PostgreSQL DDL docs.

## orm-n-plus-one

Status: draft
Triggered by: list endpoint returns nested data.
Model failure: loops over rows and performs per-row query or lazy relation access.
Blast radius: latency and DB load grow with result count.
Detect: query in loop; lazy relation access in serialization; Mongo `.find()` inside loop.
Safe pattern: join/prefetch/batch lookup; cap page size; validate query count.
Verifier: test query count for list endpoint and representative page size.
Escape hatch: bounded list of very small fixed size, documented.
Sources: PostgreSQL performance tips, MongoDB indexing strategies.

## select-star-public-response

Status: draft
Triggered by: endpoint query or repository powering public response.
Model failure: `SELECT *` or full document fetch is returned/mapped wholesale.
Blast radius: field leak and accidental contract expansion.
Detect: `SELECT *`, ORM entity returned directly, Mongo projection missing on public path.
Safe pattern: explicit column/projection list matched to response schema.
Verifier: contract test forbids internal fields.
Escape hatch: internal migration/admin script.
Sources: OWASP API3:2023, OpenAPI 3.1.

## db-timeout-missing

Status: draft
Triggered by: DB query in request path or worker.
Model failure: uses default unlimited statement/query timeout.
Blast radius: hung requests, worker starvation, pool exhaustion.
Detect: DB client/query has no context/deadline/statement timeout.
Safe pattern: request deadline propagated to DB; statement/lock timeout configured per role/session/path.
Verifier: slow query test aborts within configured budget.
Escape hatch: offline maintenance job with explicit long timeout and isolation.
Sources: PostgreSQL runtime client config, Go database cancel operations.

## mongo-index-without-query-shape

Status: draft
Triggered by: adding Mongo query or index.
Model failure: creates index on a field "just in case" or wrong compound order.
Blast radius: write amplification, unused indexes, slow sort/range queries.
Detect: index does not match equality/sort/range query shape.
Safe pattern: derive compound index from query pattern using ESR guideline.
Verifier: `explain()` confirms index use for target query.
Escape hatch: low-volume collection with explicit growth cap.
Sources: MongoDB indexing strategies, MongoDB ESR guideline.

## mongo-weak-critical-write-concern

Status: draft
Triggered by: critical writes: payments, account state, order state, audit.
Model failure: relies on default write concern without deciding durability semantics.
Blast radius: acknowledged state may be weaker than product invariant expects.
Detect: critical write path has no documented write concern/read concern policy.
Safe pattern: choose write concern/read concern based on consistency requirement; document tradeoff.
Verifier: integration/config test asserts client/session settings.
Escape hatch: cache/analytics/non-critical ephemeral data.
Sources: MongoDB write concern, MongoDB transactions.

## retry-without-jitter-or-cap

Status: production-tested (forward-test 007, 2026-07-10)
Triggered by: transient failure handling for HTTP/DB/queue calls.
Model failure: unbounded retry, fixed sleep, no jitter, no max elapsed time, retries non-idempotent operation.
Blast radius: retry storm, duplicate side effects, overload amplification.
Detect: retry loop lacks cap/jitter/idempotency check or ignores `Retry-After`.
Safe pattern: bounded exponential backoff with jitter; retry only idempotent or idempotency-protected operations.
Verifier: test retry count/timing and non-retry on non-idempotent path.
Escape hatch: single local in-memory retry with no external side effect.
Sources: AWS Reliability Pillar, Azure Retry pattern, Azure Retry Storm antipattern.

## circuit-breaker-missing-on-fragile-dependency

Status: draft
Triggered by: hot path calls unreliable/slow downstream.
Model failure: every request calls downstream until downstream failure consumes threads/pool/timeouts.
Blast radius: cascading failure.
Detect: high-volume call has timeout and retry but no fail-fast/degraded behavior.
Safe pattern: timeout + circuit breaker or budgeted fallback/degraded response.
Verifier: downstream-failure test proves bounded latency and no retry storm.
Escape hatch: low-volume admin path with manual operator use.
Sources: Azure Circuit Breaker pattern, Google SRE Cascading Failures.

## queue-consumer-not-idempotent

Status: production-tested (forward-test 006, 2026-07-10)
Triggered by: background worker, webhook handler, message queue consumer.
Model failure: assumes exactly-once delivery and writes side effects directly.
Blast radius: duplicate side effects, inconsistent state after redelivery.
Detect: consumer lacks dedupe key, idempotent state transition, or processed-message table.
Safe pattern: at-least-once assumption; idempotency key/dedupe; transactional inbox/outbox where needed.
Verifier: process same message twice; assert single side effect and stable state.
Escape hatch: read-only analytics consumer where duplicates are intentionally aggregated downstream.
Sources: AWS Reliability Pillar, Stripe idempotency.

## worker-unbounded-concurrency

Status: draft
Triggered by: batch job, queue worker, goroutines/tasks/promises over collection.
Model failure: spawns one concurrent task per item without limit or backpressure.
Blast radius: DB/API pool exhaustion, memory blowup, rate-limit bans.
Detect: `Promise.all(items.map(...))`, unbounded goroutines, `asyncio.gather` over unbounded input.
Safe pattern: bounded worker pool; respect downstream capacity; propagate cancellation.
Verifier: test max concurrency; load test or fake downstream asserts cap.
Escape hatch: collection size proven tiny and bounded.
Sources: Google SRE Handling Overload, Node event loop guidance, Go context docs, Python asyncio docs.

## timeout-without-cancellation-propagation

Status: draft
Triggered by: request deadline, cancellation, user disconnect, job shutdown.
Model failure: sets timeout at outer layer but inner DB/HTTP/tasks continue running.
Blast radius: wasted work, resource leak, inconsistent side effects.
Detect: timeout wrapper around call without context/signal passed into dependency.
Safe pattern: propagate context/AbortSignal/cancellation token to every blocking operation.
Verifier: cancellation test observes downstream operation stops.
Escape hatch: non-cancellable legacy dependency isolated in worker with hard process/job timeout.
Sources: Go context docs, Python asyncio docs, Node AbortController docs.

## event-loop-blocking

Status: production-tested (forward-test 108, 2026-07-10)
Triggered by: Node request path with crypto, compression, JSON, file IO, loops, sync DB/client calls.
Model failure: uses sync or CPU-heavy work inside request handler.
Blast radius: all clients stall because event loop is blocked.
Detect: `fs.*Sync`, large JSON operations, CPU loop, sync crypto in handler.
Safe pattern: async APIs, worker thread/process, streaming, input size cap.
Verifier: concrete proof of bounded work — row-cap test, streamed-response assertion, or event-loop delay benchmark. A comment claiming the dataset is small does not count.
Escape hatch: CLI script or one-shot startup work.
Sources: Node "Don't Block the Event Loop", Express performance practices.

## go-http-server-no-timeouts

Status: draft
Triggered by: creating or reviewing a Go HTTP server entrypoint.
Model failure: serves with `http.ListenAndServe(addr, handler)` or a bare `&http.Server{Addr, Handler}` — all server timeouts are zero.
Blast radius: per Go docs, zero means no timeout at all: slow/stalled clients (slowloris) hold connections and goroutines indefinitely; file descriptor and memory exhaustion; outage under trivial attack or bad client.
Detect: package-level `http.ListenAndServe(...)` call; `http.Server` literal with neither `ReadTimeout` nor `ReadHeaderTimeout` set.
Safe pattern: construct `http.Server` with `ReadHeaderTimeout` (preferred per docs — lets handlers own body deadlines), plus `ReadTimeout`/`WriteTimeout`/`IdleTimeout` chosen for the workload; pair with `Server.Shutdown` for graceful stop.
Verifier: startup code review or test asserting server config fields are non-zero; slow-client test where feasible.
Escape hatch: localhost-only dev/test servers, pprof/debug listeners on private interfaces, and tests using `httptest.Server`.
Sources: pkg.go.dev/net/http `Server` field docs (zero or negative value means no timeout; `ReadHeaderTimeout` falls back to `ReadTimeout`), verified 2026-07-10 against installed Go 1.26 `go doc net/http.Server`.

## go-goroutine-without-lifecycle

Status: production-tested (forward-test 009, 2026-07-10)
Triggered by: `go func()` in request/job/server path.
Model failure: launches goroutine without context, errgroup, wait, panic recovery, or bounded lifetime.
Blast radius: leaked work, ignored errors, process crash, data race.
Detect: `go` statement not tied to `errgroup`, context, worker pool, or lifecycle manager.
Safe pattern: `errgroup.WithContext`, bounded worker pool, explicit error propagation.
Verifier: cancellation test; goroutine count does not grow after request/job cancellation.
Escape hatch: process-lifetime background goroutine registered in server lifecycle.
Sources: Effective Go, Go context docs, golangci-lint linters.

## go-ignored-error

Status: draft
Triggered by: any Go call returning `error`.
Model failure: `_ =`, missing check, or log-and-continue where invariant requires stop.
Blast radius: silent data loss and corrupted state.
Detect: unchecked error or ignored close/commit/rollback errors.
Safe pattern: handle, wrap with context, or explicitly document safe ignore.
Verifier: `errcheck` clean or suppressions have reason.
Escape hatch: documented best-effort cleanup where ignoring is harmless.
Sources: Go Code Review Comments, golangci-lint `errcheck`.

## python-swallowed-exception

Status: draft
Triggered by: broad exception handling.
Model failure: `except Exception: pass`, logs without traceback, or returns default success.
Blast radius: silent data loss and false success.
Detect: broad except with no re-raise, no typed recovery, no `logging.exception`.
Safe pattern: catch specific exceptions; recover explicitly; log with traceback and fail closed when invariant unknown.
Verifier: test error path returns failure and logs exception.
Escape hatch: best-effort cleanup with comment and metric.
Sources: Python exceptions docs, Python logging docs, Ruff rules.

## python-async-cancel-swallowed

Status: production-tested (forward-test 010, 2026-07-10)
Triggered by: `asyncio` worker, request handler, background task.
Model failure: catches `BaseException`/broad exception and swallows cancellation, or creates task without awaiting/cancelling.
Blast radius: shutdown hangs, leaked task, partial side effect.
Detect: `create_task` with no lifecycle; broad except in async function; missing `finally` cleanup.
Safe pattern: `TaskGroup` or owned task registry; re-raise cancellation; use `asyncio.timeout`.
Verifier: cancellation test terminates promptly and cleanup runs.
Escape hatch: fire-and-forget telemetry with bounded queue and shutdown drain.
Sources: Python asyncio tasks docs.

## ts-floating-promise

Status: draft
Triggered by: async function call in request/worker path.
Model failure: starts promise without await/return/catch/void marker.
Blast radius: unhandled rejection, lost sequencing, side effect after response.
Detect: `no-floating-promises` lint hit or promise-valued statement.
Safe pattern: await, return, catch with explicit error handling, or `void` only for intentional detached work with lifecycle.
Verifier: `@typescript-eslint/no-floating-promises` enabled and clean.
Escape hatch: intentional background fire-and-forget registered in job supervisor.
Sources: typescript-eslint no-floating-promises, Node security docs.

## ts-any-at-boundary

Status: draft
Triggered by: request parsing, external API response, DB document, message payload.
Model failure: uses `any` and trusts shape without runtime validation.
Blast radius: runtime crash, bad writes, security bypass through malformed input.
Detect: `any`, `as unknown as`, unchecked JSON parse on boundary.
Safe pattern: runtime validation schema at boundary; `unknown` before validation; typed domain object after validation.
Verifier: malformed payload tests fail safely.
Escape hatch: generated trusted client with contract tests.
Sources: TypeScript Handbook, typescript-eslint no-explicit-any, JSON Schema 2020-12.

## observability-no-correlation-id

Status: draft
Triggered by: new service, endpoint, worker, outbound call.
Model failure: logs events without request/job/correlation id.
Blast radius: production incident cannot be traced across services.
Detect: log statements lack trace/request/job id or context propagation.
Safe pattern: correlation id generated/accepted at boundary and propagated through logs/traces/outbound calls.
Verifier: integration test or smoke request shows id in response header/log/trace.
Escape hatch: one-shot local script.
Sources: OpenTelemetry docs, Google SRE monitoring.

## metrics-high-cardinality

Status: draft
Triggered by: adding metrics labels.
Model failure: uses user id, email, raw path, request id, UUID, or error message as label.
Blast radius: monitoring cardinality explosion and cost/perf incident.
Detect: metric labels include unbounded values.
Safe pattern: bounded labels: route template, status class, dependency name, operation, error code.
Verifier: code review plus metric cardinality check in tests where possible.
Escape hatch: tracing attributes or logs where high-cardinality values are appropriate and sampled/retained safely.
Sources: OpenTelemetry docs, Google SRE monitoring.

## test-only-happy-path

Status: draft
Triggered by: any backend feature touching contracts, auth, DB, side effects, queues.
Model failure: adds only success test or no tests.
Blast radius: regressions in error path, authorization, rollback, retry, compatibility.
Detect: changed surface has no tests for failure/permission/boundary/idempotency path.
Safe pattern: proof matrix based on changed blast radius.
Verifier: cite exact test names for success, error, permission, boundary, recovery.
Escape hatch: pure refactor with unchanged behavior and existing covering tests.
Sources: pytest docs, Pact docs, Testcontainers docs.

## dependency-cargo-cult

Status: production-tested (forward-test 013, 2026-07-10)
Triggered by: stack choice, dependency recommendation, replacing custom code with a library.
Model failure: recommends a popular library without mapping it to project fit, failure removed, integration boundary, verifier, or escape hatch.
Blast radius: new abstraction hides transaction/auth/retry/migration semantics; project gains maintenance load without reducing production risk.
Detect: dependency added or recommended with no lockfile/version check, no official docs check, no test/check command, and no stated failure mode.
Safe pattern: run the dependency gate: current project fit, failure removed, integration boundary, verifier, escape hatch, removal path.
Verifier: recommendation cites official docs or installed version and adds the first proof command/test before relying on the library.
Escape hatch: exploratory prototype explicitly marked disposable.
Sources: official docs for the chosen library, project lockfile, `library-decisions.md`.

## framework-rewrite-as-cleanup

Status: production-tested (forward-test 014, 2026-07-10)
Triggered by: messy existing backend, retrofit/hardening request, framework comparison.
Model failure: recommends migrating Express to Fastify/NestJS, Flask/FastAPI to Django, or similar rewrites before mapping current P0/P1 risks.
Blast radius: rewrite delays fixes for auth, tenancy, migrations, tests, timeouts, and observability; may ship new regressions with old risks preserved.
Detect: answer starts with new framework choice before inventory of current framework, DB, migrations, tests, CI, queues, and public contracts.
Safe pattern: inventory first, harden current boundaries, introduce new library/framework only at one boundary with verifier; full migration needs explicit product/ops reason.
Verifier: staged plan lists current-stack checks and proves at least one risk reduction before any migration work.
Escape hatch: current framework is unsupported, blocks required security fixes, or the user explicitly asks for a migration project.
Sources: `stack-recipes.md`, `codebase-fit.md`, official docs for old and new frameworks.
