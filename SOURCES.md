# backend-craft source map

This file is the intake map for turning external material into backend-craft
rules. A source is useful only when it can produce one of these artifacts:

- a failure card: common agent failure, blast radius, safe pattern, verifier
- a playbook step: when to read it, what to inspect, what to change
- a checker: linter, Semgrep/ast-grep/CodeQL rule, contract diff, test command

Prefer primary sources: official docs, standards, mature project docs, and
widely used tool documentation. Blog posts are allowed only as secondary context
or war stories, never as the rule authority.

## Security and API risk

| Source | Use for | Distill into |
|---|---|---|
| OWASP API Security Top 10 2023: https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | API-specific auth, object-level auth, property-level auth, resource consumption, SSRF | `auth-tenancy-security.md`, API failure cards |
| OWASP ASVS 5.0: https://owasp.org/www-project-application-security-verification-standard/ | verification requirements, security controls, review severity | `backend-reviewer` standards, security checklist |
| OWASP REST Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html | REST auth, TLS, JWT, status codes, management endpoints | API/security playbooks |
| OWASP Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html | deny-by-default authorization, object authorization | BOLA/BOPLA cards |
| OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | security event logging, data not to log | observability and PII cards |
| MITRE CWE Top 25 2025: https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html | vulnerability prevalence and severity weighting | reviewer severity calibration |

## API contracts

| Source | Use for | Distill into |
|---|---|---|
| OpenAPI Specification 3.1: https://spec.openapis.org/oas/v3.1.0.html | machine-readable API contracts, schemas, auth, webhooks | contract-change playbook |
| JSON Schema 2020-12: https://json-schema.org/draft/2020-12 | request/response validation semantics | schema validation rules |
| Google API Improvement Proposals: https://google.aip.dev | resource naming, pagination, standard methods, long-running operations | API design defaults |
| AIP-158 Pagination: https://google.aip.dev/158 | pagination as a compatibility decision | `missing-pagination-at-launch` card |
| Stripe idempotent requests: https://docs.stripe.com/api/idempotent_requests | safe retry for mutating requests | idempotency cards |
| Stripe idempotency article: https://stripe.com/blog/idempotency | distributed failure framing for idempotent endpoints | reliability playbooks |
| Pact docs: https://docs.pact.io/ | consumer-driven contract tests | contract testing verifier |
| oasdiff: https://github.com/oasdiff/oasdiff | OpenAPI breaking-change detection | checker integration |

## Reliability and operations

| Source | Use for | Distill into |
|---|---|---|
| Google SRE, Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/ | golden signals, alerting signal quality | observability playbook |
| Google SRE, Handling Overload: https://sre.google/sre-book/handling-overload/ | overload, degradation, throttling | backpressure cards |
| Google SRE, Cascading Failures: https://sre.google/sre-book/addressing-cascading-failures/ | retry storms, resource exhaustion, overload feedback loops | reliability severity |
| AWS Reliability Pillar: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html | idempotency, retries, throttling, failure recovery | start-mode architecture checks |
| Azure Retry pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/retry | retry scope and transient failures | retry card safe pattern |
| Azure Circuit Breaker pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker | fail-fast around unhealthy dependency | circuit breaker cards |
| Azure Bulkhead pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead | isolation between workloads/tenants/dependencies | bulkhead cards |
| Azure Retry Storm antipattern: https://learn.microsoft.com/en-us/azure/architecture/antipatterns/retry-storm/ | retry amplification and `Retry-After` | retry storm verifier |
| OpenTelemetry docs: https://opentelemetry.io/docs/ | traces, metrics, logs, semantic conventions | observability rules |

## Databases

| Source | Use for | Distill into |
|---|---|---|
| PostgreSQL performance tips: https://www.postgresql.org/docs/current/performance-tips.html | query plans and EXPLAIN | slow-query playbook |
| PostgreSQL transaction isolation: https://www.postgresql.org/docs/current/transaction-iso.html | isolation levels, anomalies, serialization | transaction cards |
| PostgreSQL explicit locking: https://www.postgresql.org/docs/current/explicit-locking.html | lock modes and DDL risk | migration cards |
| PostgreSQL ALTER TABLE: https://www.postgresql.org/docs/current/sql-altertable.html | table lock levels and DDL behavior | online migration playbook |
| PostgreSQL client runtime config: https://www.postgresql.org/docs/current/runtime-config-client.html | statement, lock, transaction timeouts | DB timeout standards |
| MongoDB transactions: https://www.mongodb.com/docs/manual/core/transactions/ | transaction cost and consistency | Mongo write cards |
| MongoDB read concern: https://www.mongodb.com/docs/manual/reference/read-concern/ | consistency semantics | Mongo verifier |
| MongoDB write concern: https://www.mongodb.com/docs/manual/reference/write-concern/ | durability semantics | critical-write card |
| MongoDB indexing strategies: https://www.mongodb.com/docs/manual/applications/indexes/ | query-supported indexes | Mongo index cards |
| MongoDB ESR guideline: https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/ | compound index field order | Mongo performance playbook |
| MongoDB connection pool overview: https://www.mongodb.com/docs/manual/administration/connection-pool-overview/ | pool sizing and wait queue | pool cards |

## Python backend

| Source | Use for | Distill into |
|---|---|---|
| Python asyncio tasks: https://docs.python.org/3/library/asyncio-task.html | cancellation, timeouts, TaskGroup | async cancellation skeletons |
| Python logging: https://docs.python.org/3/library/logging.html | structured exception logging | no-swallow cards |
| Python exceptions: https://docs.python.org/3/library/exceptions.html | exception hierarchy and handling | exception cards |
| FastAPI SQL databases: https://fastapi.tiangolo.com/tutorial/sql-databases/ | FastAPI persistence integration shape | `stack-recipes.md`, Python API recipe |
| FastAPI dependencies: https://fastapi.tiangolo.com/reference/dependencies/ | dependency injection for auth/session/tenant context | FastAPI recipe |
| FastAPI OAuth2 tutorial: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/ | baseline auth flow examples | security adapter |
| Django deployment checklist: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/ | deployment/security release checks | Django/DRF recipe |
| DRF permissions: https://www.django-rest-framework.org/api-guide/permissions/ | endpoint/object permission model | auth cards, Django recipe |
| DRF serializers: https://www.django-rest-framework.org/api-guide/serializers/ | boundary DTOs and field control | BOPLA/mass-assignment cards |
| DRF validators: https://www.django-rest-framework.org/api-guide/validators/ | validation behavior | boundary validation cards |
| SQLAlchemy asyncio: https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html | AsyncSession ownership and concurrency | Python DB adapter |
| SQLAlchemy session basics: https://docs.sqlalchemy.org/en/latest/orm/session_basics.html | session lifecycle and unit of work | transaction cards |
| SQLAlchemy transactions: https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html | transaction boundaries | transaction cards |
| Alembic docs: https://alembic.sqlalchemy.org/ | migration workflow | migration playbook |
| Alembic cookbook: https://alembic.sqlalchemy.org/en/latest/cookbook.html | production migration patterns | migration playbook |
| Pydantic docs: https://docs.pydantic.dev/latest/ | Python boundary validation | `library-decisions.md`, FastAPI recipe |
| pydantic-settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | typed configuration | config boundary rules |
| HTTPX timeouts: https://www.python-httpx.org/advanced/timeouts/ | explicit outbound HTTP budgets | timeout cards |
| HTTPX async support: https://www.python-httpx.org/async/ | async client lifecycle | Python async adapter |
| Celery tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html | task idempotency, acknowledgement, retry behavior | queue cards |
| Celery workers: https://docs.celeryproject.org/en/latest/userguide/workers.html | worker lifecycle and shutdown | worker cards |
| pytest parametrization: https://docs.pytest.org/en/stable/how-to/parametrize.html | boundary/failure-path test matrix | testing playbooks |
| OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/ | Python traces/metrics/logs | observability recipe |
| Testcontainers Python: https://testcontainers-python.readthedocs.io/ | real dependency integration tests | DB test verifier |
| Ruff rules: https://docs.astral.sh/ruff/rules/ | project-local lint rule mapping | checker bridge |
| mypy config strict: https://mypy.readthedocs.io/en/stable/config_file.html | type strictness and gradual adoption | retrofit type plan |

## Go backend

| Source | Use for | Distill into |
|---|---|---|
| Effective Go: https://go.dev/doc/effective_go | idioms, errors, goroutines | language adapter |
| Go net/http package: https://pkg.go.dev/net/http | stdlib server/client behavior; Server timeout zero-values mean no timeout (verified via `go doc net/http.Server`, Go 1.26) | Go stack recipe, `go-http-server-no-timeouts` card, `go.listen-and-serve-no-timeouts` + `go.server-missing-read-timeouts` checkers |
| Go context cancellation for database ops: https://go.dev/doc/database/cancel-operations | context propagation and cleanup | context cards |
| Go Code Review Comments: https://go.dev/wiki/CodeReviewComments | idiomatic review checks | Go review adapter |
| chi router: https://github.com/go-chi/chi | idiomatic lightweight routing/middleware | `library-decisions.md`, Go recipe |
| pgx: https://github.com/jackc/pgx | Postgres driver/toolkit choices | Go persistence recipe |
| pgx package docs: https://pkg.go.dev/github.com/jackc/pgx | API-level Postgres behavior | Go persistence adapter |
| sqlc docs: https://docs.sqlc.dev/ | type-safe code generation from SQL | Go library decisions |
| golang-migrate: https://github.com/golang-migrate/migrate | migration workflow | migration recipe |
| slog package: https://pkg.go.dev/log/slog | structured logging | Go observability adapter |
| Go slog blog: https://go.dev/blog/slog | structured logging design | Go observability adapter |
| Go errgroup: https://pkg.go.dev/golang.org/x/sync/errgroup | goroutine cancellation/error propagation | concurrency cards |
| OpenTelemetry Go: https://opentelemetry.io/docs/languages/go/ | Go traces/metrics | observability recipe |
| Testcontainers Go: https://golang.testcontainers.org/ | real dependency integration tests | DB test verifier |
| golangci-lint linters: https://golangci-lint.run/docs/linters/ | errcheck, govet, gosec, contextcheck | checker bridge |

## TypeScript and Node backend

| Source | Use for | Distill into |
|---|---|---|
| Node security best practices: https://nodejs.org/learn/getting-started/security-best-practices | Node-specific threat model | Node security cards |
| Node event loop guidance: https://nodejs.org/learn/asynchronous-work/dont-block-the-event-loop | blocking sync work and CPU hotspots | event-loop cards |
| Node AbortController API: https://nodejs.org/api/globals.html | cancellation/timeouts with AbortSignal | TS async skeleton |
| Express security best practices: https://expressjs.com/en/advanced/best-practice-security.html | Express production security | framework adapter |
| Express performance best practices: https://expressjs.com/en/advanced/best-practice-performance.html | production performance settings | framework adapter |
| Fastify validation and serialization: https://fastify.io/docs/latest/Reference/Validation-and-Serialization/ | JSON Schema request/response validation | TS stack recipe |
| Fastify TypeScript: https://fastify.io/docs/latest/Reference/TypeScript/ | TS integration patterns | TS stack recipe |
| Fastify type providers: https://fastify.io/docs/latest/Reference/Type-Providers/ | schema-to-type integration | TS boundary recipe |
| NestJS docs: https://docs.nestjs.com/ | modular backend framework model | NestJS recipe |
| NestJS pipes: https://docs.nestjs.com/pipes | validation/transformation pipeline | boundary validation cards |
| NestJS validation: https://docs.nestjs.com/techniques/validation | DTO validation approach | NestJS recipe |
| Zod docs: https://zod.dev/ | TS runtime validation | library decisions |
| Valibot docs: https://valibot.dev/ | modular TS runtime validation | library decisions |
| Prisma Migrate: https://www.prisma.io/docs/orm/prisma-migrate | Prisma schema migration workflow | migration/library decisions |
| Drizzle migrations: https://orm.drizzle.team/docs/migrations | Drizzle migration workflow | migration/library decisions |
| Drizzle transactions: https://orm.drizzle.team/docs/transactions | transaction behavior | TS persistence adapter |
| Kysely docs: https://kysely.dev/ | type-safe SQL query builder | TS persistence recipe |
| BullMQ docs: https://docs.bullmq.io/ | Redis-backed queue behavior | queue recipe |
| BullMQ idempotent jobs: https://docs.bullmq.io/patterns/idempotent-jobs | duplicate-safe jobs | queue idempotency cards |
| BullMQ retrying jobs: https://docs.bullmq.io/guide/retrying-failing-jobs | retry/backoff behavior | retry cards |
| Pino docs: https://getpino.io/ | structured JSON logging | TS observability adapter |
| Node fetch with Undici: https://nodejs.org/learn/getting-started/fetch | outbound HTTP client baseline | timeout/cancellation cards |
| Undici docs: https://undici.nodejs.org/ | Node HTTP client details | TS outbound HTTP adapter |
| OpenTelemetry JS: https://opentelemetry.io/docs/languages/js/ | JS traces/metrics/logs | observability recipe |
| Vitest docs: https://vitest.dev/ | TS test runner | testing recipe |
| TypeScript Handbook: https://www.typescriptlang.org/docs/handbook/2/basic-types.html | `any`, `unknown`, strictness | TS adapter |
| typescript-eslint no-floating-promises: https://typescript-eslint.io/rules/no-floating-promises/ | unhandled promise checks | checker bridge |
| typescript-eslint no-explicit-any: https://typescript-eslint.io/rules/no-explicit-any/ | type escape hatch checks | checker bridge |

## Static analysis and dependency checking

| Source | Use for | Distill into |
|---|---|---|
| Semgrep taint mode: https://docs.semgrep.dev/writing-rules/data-flow/taint-mode/overview | cross-language taint rules for injection/SSRF | rules/semgrep |
| ast-grep YAML rules: https://ast-grep.github.io/reference/yaml.html | syntax-aware local checks and rewrites | rules/ast-grep |
| CodeQL docs: https://codeql.github.com/docs/ | deep semantic analysis when projects support it | optional hardening |
| OWASP Dependency-Check: https://owasp.org/www-project-dependency-check/ | dependency vulnerability scanning | supply-chain checks |
| OWASP Dependency-Track: https://owasp.org/www-project-dependency-track/ | SBOM-driven dependency risk | mature org mode |

## Extraction rule

For each source section, extract no more than the facts needed for agent
behavior:

1. Situation: when the agent should care.
2. Failure: what the agent tends to write incorrectly.
3. Blast radius: what breaks in production.
4. Safe pattern: concrete implementation shape.
5. Verifier: test, trace, diff, linter, query plan, or migration dry run.
6. Escape hatch: when the rule does not apply.

Do not copy broad prose into the skill. Convert prose into decisions.
