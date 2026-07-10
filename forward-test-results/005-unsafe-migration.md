# forward-test 005: unsafe-migration

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong: matches the reference's verifier list exactly — migration up on throwaway DB proving pre-existing-row backfill (the actual backfill claim), rollback dry run, NOT NULL enforcement via IntegrityError, default-on-omitted-insert, and an API contract non-leak test; pytest output inspected (18 passed). Lock analysis is documented per DDL statement. Only weakness: dry runs are SQLite, so Postgres lock behavior is argued, not exercised.

## Prompt

```text

```

## References loaded (from agent's 'Files read')

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md

## Judge summary

Excellent answer. Impact Read first, correct routing to persistence-migrations.md, PG-version-aware expand/contract with real lock analysis, batched SKIP LOCKED backfill, tested up+rollback dry runs on a throwaway DB, contract non-leak test, and a genuinely non-obvious catch (db.py silently skipping all migrations after 001, fixed and proven). All disk claims verified. Only soft gaps: replication lag is mitigated but never named, and no explicit prod-like-rehearsal/maintenance-window note for the Postgres path.

## Misses

- Replication lag never explicitly named: batched backfill 'looped with sleeps' implicitly mitigates replica lag but the answer does not mention monitoring replication lag / pausing batches when replicas fall behind
- No explicit production-like rehearsal note: the dry run is SQLite-only; the answer never states that the Postgres choreography must be rehearsed on a production-like database or scheduled in a maintenance window if lock_timeout retries keep failing (the reference's 'production-like dry run or explicit maintenance window' rule is only partially satisfied)

## Changes needed in skill/reference/failure card

- In /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md, extend the 'Migrations need deploy choreography' backfill step to: 'backfill in bounded batches; between batches monitor replica lag and throttle/pause when replicas fall behind' so replication lag is named, not just implied by sleeps
- In the same file's 'Online DDL must be proved' section, add: 'A local/SQLite dry run does not count as production-like; state explicitly which engine the dry run ran on and require a prod-like rehearsal or a maintenance-window fallback if lock_timeout retries are exhausted'

## Tested agent answer (verbatim)

````text
All 18 tests pass (12 pre-existing in `test_app.py` — the on-disk file has more tests than my initial read context suggested — plus my 6 new ones). The work is complete. Final answer follows.

---

## Task: add a NOT NULL + DEFAULT column to `invoices` (biggest, hottest table) and backfill old rows

**Assumption stated:** the task names no column, so I added `currency TEXT NOT NULL DEFAULT 'USD'`. The plan is identical for any constant-default column. The fixture runs SQLite; `migrations/001_init.sql` explicitly says invoices is 10M+ rows in production and any ALTER/backfill must be online, so the migration is written to be online-safe and carries the production (Postgres) choreography with it.

### Impact Read (per backend-craft)
- **Public contracts:** unchanged. Every invoice read uses explicit column projections (no `SELECT *`), so the new column cannot leak into responses — verified by test.
- **Data:** one additive (expand-only) column on `invoices`; no destructive step. Rollback is `DROP COLUMN` (metadata-only in SQLite ≥3.35 and Postgres).
- **Auth/tenant:** untouched.
- **Side effects:** none; pure DDL + catalog-level backfill.
- **Hot-table risk:** handled by choosing the metadata-only DDL form and documenting lock behavior.

### Changes made
1. **`/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/002_add_invoice_currency.sql`** (new)
   - Executable statement: `ALTER TABLE invoices ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD';` — in SQLite this is metadata-only and existing rows read the default, which *is* the backfill for a constant default.
   - Header documents the production Postgres choreography (see below) and the rollback statement.
2. **`/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py`** (edited)
   - Bug fixed in passing: the builder hardcoded `001_init.sql`, so any new migration would silently never run. It now applies every `migrations/*.sql` in sorted (numeric-prefix) order.
3. **`/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_invoice_currency.py`** (new) — 6 tests:
   - throwaway-DB up-migration run proving rows inserted **before** 002 come out `'USD'`/non-null (the real backfill proof),
   - throwaway-DB rollback dry run (`DROP COLUMN` restores old shape),
   - seeded rows have the default; omitted-column inserts get the default; `NULL` insert raises `IntegrityError`; existing `/invoices/{id}/pay` response contract unchanged (no `currency` key).

### Production choreography (Postgres, 10M+ rows — embedded in the migration header)
- **Fast path (PG ≥ 11, constant non-volatile default — this case):** `SET lock_timeout = '2s'; ALTER TABLE invoices ADD COLUMN currency text NOT NULL DEFAULT 'USD';` is catalog-only (no rewrite; the default is stored as the "missing value", logically backfilling all old rows). It still needs a brief ACCESS EXCLUSIVE lock, so run with a short `lock_timeout` and retry with backoff rather than queueing behind/ahead of traffic. **No physical backfill UPDATE is needed or should be run.**
- **Slow path (PG < 11, volatile default, or per-row computed values):** expand/contract — (1) add nullable column (metadata-only), (2) `SET DEFAULT` for new rows, (3) deploy code writing the column, (4) backfill in bounded batches with `WITH batch AS (SELECT id ... WHERE currency IS NULL ORDER BY id LIMIT 5000 FOR UPDATE SKIP LOCKED) UPDATE ...`, looped with sleeps, (5) `ADD CONSTRAINT ... CHECK (currency IS NOT NULL) NOT VALID` then `VALIDATE CONSTRAINT` (SHARE UPDATE EXCLUSIVE — doesn't block reads/writes), (6) on PG ≥ 12 `SET NOT NULL` (uses the validated check, skips the scan) and drop the redundant check.
- Any future index on the column: `CREATE INDEX CONCURRENTLY`, outside a transaction.
- **Rollback:** `ALTER TABLE invoices DROP COLUMN currency;` — safe because no reader uses `SELECT *`.

### Proof (final proof contract)
- `pytest -q` in the fixture venv: **18 passed** (12 pre-existing + 6 new), 0 failures.
- Migration up on a throwaway DB: `test_migration_backfills_preexisting_rows` PASSED.
- Rollback dry run on a throwaway DB: `test_migration_rollback_drop_column` PASSED.
- Contract diff: `test_existing_api_contract_unchanged` PASSED (no new key in existing responses).

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/001_init.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml
````
