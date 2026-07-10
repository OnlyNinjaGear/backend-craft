# Library decisions

Read this when choosing a stack, adding a dependency, replacing custom backend
code with a library, or reviewing whether an existing library choice is still
serving the project.

Failure cards: `dependency-cargo-cult`, `framework-rewrite-as-cleanup`.

## Contents

- Rule
- Dependency gate
- Fast replacements for fragile custom code
- Python defaults
- Go defaults
- TypeScript/Node defaults
- Review output

## Rule

Prefer the standard library and project-local patterns until a library clearly
removes a production risk or a large amount of repeated, fragile code.

Add or recommend a library only when it provides at least one of:

- validated external boundaries: request, response, config, webhook, message
- type-safe or migration-safe persistence behavior
- battle-tested retry, queue, idempotency, timeout, or cancellation semantics
- standard observability output: traces, metrics, structured logs
- contract checks: OpenAPI diff, generated clients, Pact
- real dependency tests: containers, ephemeral DBs, fixture orchestration
- security primitives that are easy to misuse by hand

Do not add a library when it only hides semantics the agent must reason about:
transactions, authorization, migration locks, retries, queue delivery, or tenant
filters.

## Dependency gate

Before adding or recommending a dependency, answer:

1. What project-local tool already solves this?
2. What failure card or repeated fragile code does the library remove?
3. Is the official documentation current enough for the version in the lockfile?
4. Where is the integration boundary: handler, repository, migration, worker,
   test, telemetry, or client?
5. What is the failure mode if the library is misconfigured?
6. What verifier proves it works: test, typecheck, migration dry run, contract
   diff, trace, or linter?
7. How can the project remove or replace it later?

If exact APIs, versions, or security settings matter, verify against official
docs or the installed package before editing. Do not guess "latest" behavior.

## Fast replacements for fragile custom code

Use these to collapse common 30-step hand work into a smaller, verifiable
workflow:

| Fragile custom work | Prefer | Verifier |
|---|---|---|
| ad hoc request/response validation | Pydantic, Fastify schemas, Zod, Valibot, DRF serializers | invalid input tests, generated schema |
| hand-managed test databases | Testcontainers or existing local service harness | integration test against real DB |
| manual OpenAPI compatibility review | oasdiff or generated-client diff | breaking-change report |
| hand-written consumer contract checks | Pact where consumers exist | provider/consumer contract run |
| custom trace/log correlation | OpenTelemetry plus structured logger | trace/log contains request/correlation id |
| untracked SQL file changes | Alembic, golang-migrate, Drizzle/Prisma migrations | dry run, rollback or forward-fix proof |
| hand-built SQL mapping boilerplate | sqlc, Kysely, Drizzle, SQLAlchemy Core/ORM | typecheck plus DB integration test |
| homemade retry loops | library/pattern with cap, jitter, cancellation, `Retry-After` handling | bounded retry test |
| in-process critical background work | Celery, BullMQ, durable queue already used by project | duplicate-delivery/idempotency test |

## Python defaults

For a new API-first service, default to:

- FastAPI for HTTP APIs when async-compatible dependency handling and OpenAPI
  generation are useful.
- Pydantic v2 for boundary validation and settings.
- SQLAlchemy 2.x plus Alembic for production Postgres control.
- HTTPX for outbound HTTP with explicit timeouts.
- pytest, Ruff, mypy or pyright according to project convention.
- OpenTelemetry Python when traces/metrics are required.
- Testcontainers or an existing local Postgres service for DB semantics.

Use Django + Django REST Framework when admin, auth, ORM, migrations, and
batteries-included product CRUD are leverage. Do not recreate Django's admin,
permission, serializer, and migration stack inside a small framework.

Use Celery when background work must survive process restarts, retry later, or
run on a worker fleet. Do not use request-local background tasks for critical
side effects.

Escape hatches:

- SQLModel can be fine for simple CRUD/prototypes, but use SQLAlchemy/Alembic
  directly when schema evolution, transactions, and query control matter.
- A synchronous stack is acceptable when the service is mostly DB-bound and the
  team knows it; async is not a quality badge.

## Go defaults

For a new small or medium API service, default to:

- `net/http` when the route surface is small and framework value is low.
- chi when route groups, middleware composition, and idiomatic context-based
  routing improve clarity.
- pgx for Postgres access.
- sqlc when SQL-first type-safe data access is a good fit.
- golang-migrate or the migration tool already standard in the org.
- `log/slog` for structured logs unless the project already uses another logger.
- `errgroup.WithContext` for request-scoped parallel work.
- OpenTelemetry Go for traces/metrics.
- Testcontainers Go or an existing local dependency harness for DB tests.

Keep SQL and transaction boundaries visible. Do not hide DB behavior behind a
generic repository if the abstraction prevents query plans, isolation choices,
or lock behavior from being reviewed.

Escape hatches:

- A heavier framework can be justified by org convention, generated APIs, or
  existing middleware, but should not be introduced for a small router problem.
- Hand-written SQL is acceptable when query count is small and tests cover it.

## TypeScript/Node defaults

For a new API-first service, choose deliberately:

- Fastify when schema validation, serialization, and throughput matter.
- NestJS when the team wants opinionated modules, dependency injection, and
  consistent enterprise structure.
- Express mainly for existing apps, small services, or ecosystem constraints;
  add validation, security, async error handling, and observability explicitly.

Boundary validation:

- Use Fastify JSON Schema route schemas when Fastify is the API layer.
- Use Zod for broad TypeScript ecosystem support and ergonomic validation.
- Use Valibot when modularity and bundle size are strong concerns.

Persistence:

- Kysely when SQL-first, type-safe query building is the right model.
- Drizzle when a TypeScript schema/migration workflow and SQL-ish control fit.
- Prisma when rapid product CRUD, generated client ergonomics, and team speed
  outweigh the need for low-level query control. Review migrations,
  transactions, raw SQL, and operational behavior carefully.

Jobs and HTTP:

- BullMQ for Redis-backed durable jobs when Redis is acceptable infrastructure.
- Node `fetch`/Undici for outbound HTTP; use explicit timeouts/cancellation.
- Pino for structured JSON logs unless the project already standardized.
- OpenTelemetry JS for tracing and metrics.
- Vitest, Node test runner, or project-local test runner according to the repo.

Escape hatches:

- Do not migrate an existing Express app to Fastify/NestJS during a feature fix
  unless the task is explicitly a framework migration.
- Do not introduce an ORM/query builder if the service has a tiny stable query
  surface and current SQL is already tested and reviewed.

## Review output

When recommending a library, state:

- chosen library and why it fits this codebase
- alternatives rejected and the concrete tradeoff
- failure card or repeated fragile workflow it addresses
- first verifier to add before relying on it
- docs/source checked, or the reason current verification is unavailable
