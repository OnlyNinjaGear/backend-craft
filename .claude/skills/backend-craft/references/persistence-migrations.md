# Persistence and migrations

Read this when touching SQL, ORM queries, MongoDB, transactions, migrations,
indexes, connection pools, soft deletes, data backfills, or DB performance.

## Data read

Identify:

- tables/collections and ownership scope
- read/write/delete semantics
- transaction boundary
- migration/deploy ordering
- query cardinality and indexes
- timeout and pool behavior

## Non-negotiables

### Transactions stay short

Do not hold a DB transaction open across network calls, email, payment, queue
publish, or slow computation. Keep lock time small.

Safe pattern:

- perform invariant-changing DB writes in one short transaction
- use outbox/inbox/state machine for external side effects
- make worker side effects idempotent

### Public queries use explicit projections

Avoid `SELECT *` and full document projection on public paths. Explicitly select
fields needed for the response or domain operation.

### No query-in-loop on unbounded lists

List endpoints and workers must not perform per-row child queries. Use joins,
prefetch, batch lookup, aggregation, or bounded worker pools.

Verifier: query-count test or query log on representative page size.

### Migrations need deploy choreography

For live systems, prefer expand/contract:

1. expand schema compatibly
2. deploy code that writes both/reads old+new
3. backfill in bounded batches; between batches monitor replica lag and
   throttle or pause when replicas fall behind
4. switch reads
5. remove old shape later

Direct destructive migrations require signoff and rollback/forward-fix plan.

### Online DDL must be proved

On Postgres, read lock behavior for the exact DDL. `ALTER TABLE` subforms can
take strong locks. For hot tables, require production-like dry run or explicit
maintenance window. A local/SQLite dry run does not count as production-like:
state which engine the dry run ran on, and require a prod-like rehearsal or a
maintenance-window fallback if `lock_timeout` retries are exhausted.

### DB operations need timeouts

Request-path queries inherit request deadlines. Workers have explicit job
budgets. DB roles/sessions should set statement/lock/transaction timeouts when
the stack supports it.

## MongoDB specifics

- Design compound indexes from query shape; use Equality, Sort, Range ordering.
- Critical writes need explicit read/write concern decision.
- Multi-document transactions have cost; use when invariants require them.
- Avoid `.find()` inside loops; prefer bulk queries or aggregation.

## Common failure cards

- `sql-string-concat`
- `db-transaction-around-network-call`
- `migration-non-online-ddl`
- `migration-no-rollback-plan`
- `orm-n-plus-one`
- `select-star-public-response`
- `db-timeout-missing`
- `mongo-index-without-query-shape`
- `mongo-weak-critical-write-concern`

## Verifiers

- migration up/down on throwaway DB
- lock analysis for hot-table DDL
- `EXPLAIN` or driver-specific query plan
- query-count integration test
- duplicate message/request idempotency test
- connection pool settings inspection
