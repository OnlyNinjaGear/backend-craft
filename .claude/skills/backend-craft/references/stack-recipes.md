# Stack recipes

Recipes are defaults, not mandates. Use them in Start mode or when a user asks
which backend stack to choose. In existing projects, inventory the current stack
before recommending changes.

Failure cards: `dependency-cargo-cult`, `framework-rewrite-as-cleanup`.

## Contents

- Selection rule
- Python: FastAPI + Postgres service
- Python: Django + DRF product backend
- Go: chi/net-http + Postgres service
- TypeScript/Node: Fastify + Postgres API
- TypeScript/Node: NestJS modular API
- Retrofit recipe
- Harden recipe
- Scaffold warning

## Selection rule

Pick the stack that makes correctness easiest for this team and product:

- API contract can be expressed and tested.
- Auth and tenant boundaries have one obvious implementation path.
- Persistence and migrations have visible semantics.
- Timeouts, retries, queues, and idempotency are not hand-waved.
- Logs, metrics, and traces can be wired before scale problems appear.
- Tests can run against real dependencies where semantics matter.

Avoid "best framework" answers. Name the product constraints that make a stack
best or risky.

## Python: FastAPI + Postgres service

Use when:

- API-first service, internal or external.
- Async HTTP clients or high concurrency are useful.
- Team is comfortable owning explicit persistence and migrations.

Default stack:

- FastAPI
- Pydantic v2 and pydantic-settings
- SQLAlchemy 2.x
- Alembic
- Postgres
- HTTPX
- pytest
- Ruff plus mypy/pyright if project convention supports typing
- OpenTelemetry Python when observability is required
- Testcontainers or existing local Postgres harness

Baseline decisions:

- Define explicit request and response DTOs; do not return ORM models from
  public endpoints.
- Use FastAPI dependencies for auth context, tenant context, and per-request DB
  session.
- Use one SQLAlchemy session per request/task. Do not share `AsyncSession`
  across concurrent tasks.
- Put all schema changes through Alembic.
- Configure outbound HTTP timeouts explicitly.
- For mutating endpoints that clients may retry, design idempotency before
  launch.
- Emit structured logs with request/correlation id and no secrets/PII.

Avoid:

- `asyncio.create_task` from request handlers for critical side effects.
- Transactions that include outbound network calls.
- SQLModel for complex production domains unless the team accepts its limits.

First proof:

- endpoint tests for success, validation error, auth/tenant denial
- DB integration test against real Postgres
- migration dry run
- type/lint command

## Python: Django + DRF product backend

Use when:

- Admin, auth, permissions, ORM, forms, and migrations are product leverage.
- The app is CRUD-heavy and wants a batteries-included framework.

Default stack:

- Django
- Django REST Framework
- Django ORM and migrations
- DRF serializers, validators, permissions
- pytest or Django test runner
- deployment checklist checks

Baseline decisions:

- Use separate serializers for create/update/read when fields differ by role or
  lifecycle.
- Enforce object permissions for tenant-owned or user-owned data.
- Use `select_related`/`prefetch_related` deliberately for list endpoints.
- Run deployment/security checks before production release.
- Treat migrations as production operations, not just generated files.

Avoid:

- Exposing model fields through generic serializers without a role/tenant review.
- Adding FastAPI-style custom infrastructure inside Django when built-in Django
  behavior already solves it.

## Go: chi/net-http + Postgres service

Use when:

- Small to medium service that values operational simplicity.
- Team wants explicit SQL, explicit errors, and predictable concurrency.

Default stack:

- `net/http` or chi
- pgx
- sqlc when SQL-first generated types are useful
- golang-migrate or existing org migration tool
- `log/slog`
- `errgroup.WithContext`
- OpenTelemetry Go
- Testcontainers Go or existing local dependency harness
- golangci-lint when already supported

Baseline decisions:

- Pass `context.Context` through DB, HTTP, and worker calls.
- Prefer bounded goroutines with visible cancellation and error propagation.
- Keep transaction boundaries near the use case being protected.
- Use request ids/correlation ids in logs.
- Review migrations for lock level, backfill strategy, and rollback/forward fix.

Avoid:

- `context.Background()` inside request paths.
- Naked goroutines that outlive request or worker shutdown.
- Ignored errors.

First proof:

- `go test ./...`
- migration dry run or test DB application
- integration test for auth/tenant or persistence behavior
- lint/vet where configured

## TypeScript/Node: Fastify + Postgres API

Use when:

- API-first service with TypeScript team.
- Route schemas and fast validation/serialization are important.

Default stack:

- Fastify
- Fastify JSON Schema route schemas, optionally Zod/Valibot at boundaries
- Kysely or Drizzle for SQL-first data access
- Postgres
- Pino
- Node `fetch`/Undici with explicit timeout/cancellation
- Vitest or project-local Node test runner
- OpenTelemetry JS
- BullMQ if durable Redis-backed jobs are required

Baseline decisions:

- Every external boundary validates runtime data before domain logic.
- Public responses use DTOs, not ORM records or database rows.
- Mutating retryable operations get idempotency keys or duplicate-safe logic.
- Every promise is awaited, returned, caught, or intentionally detached with
  lifecycle/error handling.
- CPU-heavy or synchronous filesystem work stays out of request handlers.

Avoid:

- `any` at public boundaries.
- Fire-and-forget jobs without shutdown/error handling.
- SQL template/string construction without parameterization.

First proof:

- project-local typecheck
- route tests for success, validation, auth/tenant denial
- DB integration test
- eslint/no-floating-promises if configured

## TypeScript/Node: NestJS modular API

Use when:

- Team wants a strong module/DI convention.
- The service has enough domain surface for NestJS structure to pay rent.
- Existing org patterns, guards, pipes, interceptors, and testing conventions are
  already Nest-based.

Default stack:

- NestJS
- ValidationPipe and explicit DTO validation
- chosen DB layer: Prisma, Drizzle, Kysely, or project-standard DB layer
- Pino or established structured logger
- OpenTelemetry JS
- project-local test runner

Baseline decisions:

- Guards enforce auth/tenant decisions; services must still defend critical
  object access.
- DTO validation does not replace authorization.
- Module boundaries should follow product domains, not database tables.
- Background work still needs durable queue semantics when side effects matter.

Avoid:

- Treating dependency injection as architecture proof.
- Introducing NestJS into a small existing Express app as incidental cleanup.

## Retrofit recipe

When attaching to an existing backend:

1. Inventory framework, package manager, DB, migration tool, queue, tests, CI,
   linters, tracing/logging, and deployment assumptions.
2. Identify the libraries already chosen by the project and use them first.
3. Map current risks to failure cards before recommending a new dependency.
4. Add or tighten verifiers before broad refactors.
5. Introduce a new library only at a single boundary and prove it with tests.

Do not start by replacing the framework. Most mid-project value comes from
making existing boundaries safer: validation, authorization, migrations,
timeouts, idempotency, tests, and observability.

## Harden recipe

For a whole-backend pass, read in this order:

1. `api-contracts.md`
2. `auth-tenancy-security.md`
3. `persistence-migrations.md`
4. `reliability-async.md`
5. `observability-ops.md`
6. `testing-verification.md`
7. `language-adapters.md`
8. `library-decisions.md`

Report P0/P1 findings first. Library recommendations belong after failure
findings unless the missing library is itself the safest fix path.

## Scaffold warning

Do not scaffold blindly. For a new service, produce a short architecture record
first:

- chosen recipe and why
- rejected recipes and why
- first irreversible decisions
- first verifier commands
- risks that need product or ops input before implementation
