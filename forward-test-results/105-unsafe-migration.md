# forward-test 105: unsafe-migration (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. 5 new pytest tests (column exists/notnull, default on new writes, NULL rejected via IntegrityError failing path, batched backfill fills only NULL rows leaving pre-set EUR rows untouched, idempotent rerun updates 0), CLI dry run on a 5000-row throwaway DB with null_before/updated/null_after counts plus rerun, and pre-existing 7 happy-path tests kept green. Grader re-ran the suite: 12 passed. Only Postgres lock behavior is unverified, and the answer says so explicitly and compensates with a mandatory prod-like rehearsal requirement baked into the 002a file.

## Prompt

```text
Add a non-null column with a default to the invoices table and backfill old rows. Invoices is our biggest, hottest table.
```

## Round-2 focus verdict

Replication-lag monitoring: SATISFIED (explicit between-batch replica-lag check with pg_stat_replication write_lag metric and pause threshold, in both answer and script docstring). Dry-run engine / SQLite-not-prod-like: SATISFIED (engine named, limitation stated, prod-like snapshot rehearsal required, maintenance-window fallback on exhausted lock_timeout retries — in answer and in 002a file).

## References loaded

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md

## Judge summary

Exemplary round-2 answer: both round-1 regressions are closed explicitly and in the artifacts, not just in prose. Grader independently verified all claims — the created migration/backfill/test files exist and match the answer, and `uv run pytest -q` reproduces 12 passed. Design shows non-obvious depth (PG11 fast-default still takes brief ACCESS EXCLUSIVE hence fail-fast lock_timeout+retry; SKIP LOCKED loop-until-zero termination correctness; non-recursive migration glob keeping postgres/ files out of the SQLite fixture). Verifier includes a failing-path test, an idempotency rerun test, and a 5000-row CLI dry run with counts, plus an honest residual-risk note that Postgres lock behavior was not exercised locally.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
# Migration 002: `invoices.currency TEXT NOT NULL DEFAULT 'USD'` — online-safe design + implementation

**Assumptions (stated, not asked):** the new column is `currency` (ISO-4217) with constant default `'USD'`; production engine is Postgres (per the online-migration note in `001_init.sql`) while the fixture runs SQLite; the column is not yet exposed in any API response, so no contract change.

**Impact Read:** no public contract change (no endpoint selects the column; no `SELECT *` on invoices); data written = one additive column + backfill on the 10M+-row hottest table; no auth/tenant boundary change; the backfill is a long-running side effect that must be idempotent and resumable; proof = new pytest coverage + CLI dry run.

## Design (production choreography, expand/contract)

- **Fast path (recommended, PG >= 11):** a single `ALTER TABLE invoices ADD COLUMN currency text NOT NULL DEFAULT 'USD'` is metadata-only ("fast default", no table rewrite; existing rows read the default from the catalog). It still takes a brief ACCESS EXCLUSIVE lock, so it runs with `SET LOCAL lock_timeout='2s'` + `statement_timeout='15s'` and an external retry loop (fail fast instead of queueing behind traffic and blocking all readers/writers). Phases b/c are skipped. — `migrations/postgres/002a_invoices_currency_expand.sql`
- **General path (PG < 11, volatile default, or old rows need a computed value):**
  1. **002a expand:** same DDL without `NOT NULL` (column nullable, default applies to new writes only).
  2. **Deploy** code that writes the column on insert paths (this app has no application insert path into invoices — only the seed — so no code change needed; noted explicitly).
  3. **002b backfill:** `scripts/backfill_invoice_currency.py` — keyset-batched (`WHERE currency IS NULL ORDER BY id LIMIT :batch`), one short transaction per batch, `--sleep` throttle, loop-until-zero-rows termination (correct even under Postgres `FOR UPDATE SKIP LOCKED`, which the docstring prescribes for prod so the backfill never queues behind live payment locks). Idempotent and resumable: predicate is `currency IS NULL`, already-set rows never touched. Between batches: monitor replica lag and pause above threshold.
  4. **002c enforce:** `CHECK (currency IS NOT NULL) NOT VALID` (brief lock, no scan) → `VALIDATE CONSTRAINT` (full scan under SHARE UPDATE EXCLUSIVE — reads/writes proceed) → on PG >= 12 `SET NOT NULL` (skips the scan by reusing the validated check) + drop the check. — `migrations/postgres/002c_invoices_currency_enforce_not_null.sql`
- **Rollback at every phase** is metadata-only and documented in the files (`DROP COLUMN`, `DROP CONSTRAINT`, `DROP NOT NULL`), all under the same `lock_timeout` discipline.
- **Lock proof requirement:** the SQLite dry run proves schema shape only, not Postgres lock behavior — the 002a file requires a rehearsal on a prod-like snapshot under concurrent write load, with a maintenance-window fallback if lock_timeout retries are exhausted.

## Files changed/created (all paths absolute)

- `.../round2/005-python-fastapi/migrations/002_add_invoice_currency.sql` — **new**: fixture migration (SQLite `ADD COLUMN ... NOT NULL DEFAULT 'USD'` is O(1) metadata; comments route prod to the postgres/ choreography).
- `.../round2/005-python-fastapi/migrations/postgres/002a_invoices_currency_expand.sql` — **new**: expand phase, fast-path vs general-path, lock/statement timeouts, retry + rollback plan.
- `.../round2/005-python-fastapi/migrations/postgres/002c_invoices_currency_enforce_not_null.sql` — **new**: NOT VALID → VALIDATE → SET NOT NULL enforcement, per-PG-version notes, rollback.
- `.../round2/005-python-fastapi/scripts/backfill_invoice_currency.py` — **new**: batched idempotent backfill; `backfill_currency(conn, *, batch_size, sleep_seconds, value) -> int` + CLI (`--database --batch-size --sleep --value`), exits 1 if NULLs remain.
- `.../round2/005-python-fastapi/app/db.py` — **modified**: `MIGRATION` (single file) replaced with `MIGRATIONS_DIR` + `_apply_migrations()` applying sorted top-level `migrations/*.sql`; deliberately non-recursive so `migrations/postgres/` never runs against the fixture.
- `.../round2/005-python-fastapi/tests/test_migration_002.py` — **new**: 5 tests.

(Full prefix for `...`: `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad`)

## Proof

- `uv run pytest -q` → **12 passed** (7 pre-existing happy-path tests unchanged and green, proving no behavior regression; migration up applied on every `reset_db`). New tests: `test_migration_applies_and_seed_rows_have_default_currency` (column exists, `notnull=1`, all 3 seed rows `USD`), `test_new_invoice_write_gets_default_currency`, `test_null_currency_is_rejected` (failing path: `sqlite3.IntegrityError`), `test_backfill_fills_only_null_rows_in_batches` (25 NULLs in batches of 10 → 25 updated, 3 pre-set `EUR` rows untouched), `test_backfill_is_idempotent_on_rerun` (second run → 0).
- **Backfill CLI dry run** on a throwaway 5,000-row file DB, batch 500: `null_before=5000 updated=5000 null_after=0`; immediate rerun: `null_before=0 updated=0 null_after=0` (idempotence/resumability proof).
- **Residual risk:** Postgres lock behavior is asserted from documented lock semantics, not exercised here (no Postgres in this environment) — hence the mandatory prod-like rehearsal step baked into 002a, per the skill's online-DDL rule.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill launch)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/migrations/001_init.sql
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/app/__init__.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/pyproject.toml
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/tests/test_app.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/005-python-fastapi/tests/conftest.py
````
