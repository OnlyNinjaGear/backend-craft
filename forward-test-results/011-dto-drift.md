# forward-test 011: dto-drift

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Full suite independently reproduced at 58 passed; targeted tests directly exercise the changed behavior: admin sees value and NULL, member never sees the key, PATCH cannot write last_login_ip/role (asserted at the DB, not just the status code), cross-tenant GET/PATCH indistinguishable 404s with no write, PATCH response asserted free of the field, plus migration up and DROP COLUMN rollback dry runs on a throwaway DB. Honest residual-risk note that no OpenAPI contract tooling exists, so enforcement rests on projections + absence tests.

## Prompt

```text

```

## References loaded (from agent's 'Files read')

- references/api-contracts.md
- references/auth-tenancy-security.md
- references/persistence-migrations.md
- references/testing-verification.md
- references/language-adapters.md
- references/codebase-fit.md

## Judge summary

Exemplary run. The agent led with a genuine Impact Read (contract, PII, tenant table, migration, and the collision with the planted mass-assignment PATCH), loaded exactly the references the routing table prescribes for those signals, and skipped the irrelevant ones. All three expected behaviors are present and test-backed. It found the non-obvious failure mode — shipping last_login_ip while PATCH /users/{id} accepted arbitrary columns would make the field spoofable — and fixed it fail-closed with DB-level proof, while also avoiding the planted BOLA pattern in its new GET endpoint. Proof claims are real: I independently reran the suite and got 58 passed, and the 13 new tests include absence assertions, cross-tenant 404 indistinguishability, and migration up/rollback dry runs. Not writing the field was explicitly scoped and justified (no login flow exists in the fixture). No skill/reference edits needed.

## Misses

- none

## Changes needed in skill/reference/failure card

- none

## Tested agent answer (verbatim)

````text
Full suite is now green — 58 passed (the concurrent session's enrichment work stabilized mid-flight; my 13 tests plus all pre-existing tests pass together).

## Summary

**Task**: expose a new `last_login_ip` field on the user object, visible to admins.

**Impact Read**: this touches an API contract (user DTO), PII (IP address), a tenant-owned table (`users`), a schema migration, and it directly collides with the mass-assignable `PATCH /users/{user_id}` — without a guard, any client could write the new server-owned column through that endpoint.

**Changes**

1. `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/003_add_user_last_login_ip.sql` — expand migration: `ALTER TABLE users ADD COLUMN last_login_ip TEXT;` nullable, no default (NULL = never logged in; no backfill possible). Metadata-only in SQLite; documented Postgres form (`inet` type, `SET lock_timeout = '2s'` + retry) and rollback (`DROP COLUMN`, contract-safe since all readers use explicit projections). Picked up automatically by `app/db.py`'s sorted-glob migration runner; seed inserts use explicit column lists so seeded users read NULL.

2. `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py`
   - New `GET /users/{user_id}`: fetches by `(id, org_id)` with org_id server-derived from the principal; cross-org and missing ids return an identical 404. Response is built from an explicit field allowlist (`_USER_PUBLIC_FIELDS`); `last_login_ip` is added opt-in only when the caller's `role == 'admin'` — the key is omitted entirely for members.
   - Hardened `PATCH /users/{user_id}` (required by this change — the new column must be server-owned): writable-field allowlist `("name", "email")`, 400 fail-closed on any other key (`last_login_ip`, `role`, `org_id`, ...), 400 on empty body, tenant-scoped UPDATE/SELECT (`AND org_id = ?`) with uniform 404, and the response projection still excludes `last_login_ip`. SQL identifiers now come only from the allowlist; values remain bound parameters.
   - Not implemented: writing `last_login_ip`. **Assumption**: population belongs to a login flow, and this fixture has no login endpoint (auth is a faked `X-User-Id` header); recording it per-request in `get_current_user` would be wrong semantics ("last seen", not "last login") and add a write per request. The column ships NULL until a login flow writes it.

3. `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_user_last_login_ip.py` — 13 tests covering the proof matrix: migration up on throwaway DB (pre-existing rows read NULL) and rollback dry run; admin sees the field (value and NULL cases); member never sees the key (even on self); cross-tenant GET/PATCH are indistinguishable 404s and write nothing; PATCH cannot set `last_login_ip` (value asserted unchanged in DB) or `role` (no escalation); PATCH response asserted free of `last_login_ip`; auth required; empty body 400.

**Proof** (final proof contract): `.venv/bin/python -m pytest` → **58 passed** (full suite, output inspected). Targeted run of `tests/test_app.py tests/test_invoice_currency.py tests/test_user_last_login_ip.py` → 31 passed, including pre-existing `test_patch_updates_name` (PATCH happy path preserved) and the migration/rollback dry runs.

**Behavior change note**: `PATCH /users/{user_id}` previously accepted arbitrary columns and cross-org ids; it now returns 400 for non-allowlisted fields and 404 for cross-org targets. This is an intentional contract tightening — leaving it open would have made the new PII field client-spoofable (worthless for the admin-forensics use case) and cross-tenant writable. All pre-existing tests still pass.

**Residual risks**: no OpenAPI snapshot/contract tooling exists in the fixture, so contract enforcement rests on the explicit projections plus the absence-assertion tests; within an org, any member may still PATCH another member's name/email (pre-existing policy, unchanged); SQLite `TEXT` does not validate IP syntax (use `inet` on Postgres); the field stays NULL until a real login flow writes it. A concurrent session added `app/enrichment.py`/observability to this fixture mid-task; it does not intersect this change and its tests pass in the final run.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/enrichment.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/001_init.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/002_add_invoice_currency.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_invoice_currency.py
````
