# Testing and verification

Read this when adding behavior, fixing bugs, reviewing code, introducing
migrations, changing contracts, touching auth, side effects, queues, or DB
queries.

## Proof matrix

Map changed surface to proof:

| Surface | Required proof |
|---|---|
| public endpoint | success, validation error, auth/permission, contract/schema |
| tenant-owned data | cross-tenant denial test |
| mutation with side effect | idempotency/duplicate test |
| DB migration | up/down or forward-fix proof, dry run |
| query performance | query count, `EXPLAIN`, index use, or bounded cardinality |
| retry/timeout | retry count, cancellation, bounded latency |
| queue/worker | duplicate delivery, poison message/dead-letter, shutdown |
| observability | correlation/log/metric assertion |

## Non-negotiables

### Changed behavior needs a failing-path test

Happy path only is not proof. Backend failures usually live in error,
permission, boundary, retry, cancellation, and rollback paths.

### Real dependencies for persistence semantics

When testing database behavior, prefer the real database engine via local
service/Testcontainers over in-memory substitutes that do not match locks,
transactions, indexes, JSON, isolation, or constraints.

### Contract checks for public APIs

If OpenAPI/Pact/generated clients exist, run the contract check. If they do not
exist and the change is public, state that residual risk.

### Read command output

A command only counts if its output was inspected. A green command that did not
exercise the changed surface is not proof.

## Useful tools

- pytest for Python test suites
- Go `go test ./...`
- Node test runner, Vitest, Jest, or project-local test script
- Testcontainers for real dependencies
- Pact for consumer-driven contracts
- oasdiff for OpenAPI breaking-change checks
- Semgrep/ast-grep for high-confidence failure signatures

## Final response pattern

Report:

- what changed
- proof commands and results
- residual risks or unavailable checks
- next highest-value hardening step when relevant
