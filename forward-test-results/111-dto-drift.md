# forward-test 111: dto-drift (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. Tests assert the exact DTO key set (contract-level forbidden-field-absence), omission-not-null for non-admins on both GET and PATCH responses, cross-org 404s, unauthenticated 401, and — critically — post-rejection DB state for both last_login_ip forgery and role escalation, so the verifier checks side effects, not just status codes. Test run independently reproduced (16 passed). Weaknesses are disclosed: migration rollback proven only on SQLite, and IP capture exercised with a single TestClient address.

## Prompt

```text

```

## Round-2 focus verdict

FOCUS 1 (admin vs public DTO split): SATISFIED — explicit serialize_user DTO with admin-of-same-org opt-in, no row spreading anywhere on the user surface. FOCUS 2 (field absent from public response): SATISFIED — key omitted (not null) for non-admins and cross-role presence leak explicitly tested on both GET and PATCH paths. FOCUS 3 (contract/permission tests): SATISFIED — exact-keyset contract assertion, member-omission, cross-org 404 (GET and PATCH), 401, forgery/escalation rejections with DB-state verification. All focus items verified against the actual working tree and a reproduced test run.

## References loaded

- SKILL.md
- api-contracts.md
- auth-tenancy-security.md
- persistence-migrations.md
- testing-verification.md
- language-adapters.md

## Judge summary

Round-2 pass at the top of the rubric. The agent ran a genuine Impact Read, loaded every routing-matched reference, and delivered exactly the fix the round-1 regression targeted: an explicit admin/public DTO split (serialize_user + USER_PUBLIC_FIELDS) where last_login_ip is opt-in for same-org admins and the key is omitted, not nulled, for everyone else, backed by 9 concrete contract/permission tests including an exact-keyset assertion and DB-state checks after rejected writes. It caught two non-obvious failure modes (the existing mass-assignment PATCH would let callers forge the new server-owned field; X-Forwarded-For spoofing absent trusted-proxy config), shipped a safe additive migration with documented rollback, and scoped correctly — flagging but not fixing the unrelated planted flaws. I independently reran the suite: 16 passed, matching the claim; all described files exist and match the summary.

## Misses

- Minor: the SQLite dry run is the only migration proof (acknowledged by the agent per the skill's own rule, so it is a disclosed limitation rather than an unnoticed gap)
- Minor: PATCH email path adds no uniqueness/format validation and the per-request UPDATE on auth could be a hot-row concern on a real multi-worker Postgres deployment — neither raised as a residual risk item, both low-impact in this fixture

## Changes needed

- none

## Tested agent answer (verbatim)

````text
Implementation complete and verified. Summary below.

## What changed

**Feature: `last_login_ip` on the user object, visible to admins only.**

1. **`/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/migrations/002_add_users_last_login_ip.sql`** (new) — `ALTER TABLE users ADD COLUMN last_login_ip TEXT;`. Additive, nullable, no default, no backfill: no table rewrite, safe expand step. Does not touch the invoices/payments tables flagged LARGE in 001. Rollback documented in the file (`DROP COLUMN`).

2. **`app/db.py`** — migration loader now applies every `migrations/*.sql` in filename order instead of only `001_init.sql`.

3. **`app/auth.py`** — capture point. The app has no login endpoint (auth is the `X-User-Id` header), so the stated assumption is: *last login = most recent authenticated request*. `get_current_user` now takes the injected `Request`, records `request.client.host` into `users.last_login_ip` (parameterized), and writes only when the value changed so steady-state requests stay read-only. `X-Forwarded-For` is deliberately not parsed — no trusted-proxy config exists, and a client-controlled header would let callers forge the audit value (deploy-time note: `uvicorn --proxy-headers` with trusted hosts).

4. **`app/main.py`** —
   - `serialize_user(row, viewer)`: explicit DTO (`id, org_id, email, name, role`); `last_login_ip` is added only when the viewer is an **admin of the same org**, and the key is *omitted* (not null) otherwise, so field presence never leaks across the role boundary.
   - New `GET /users/{user_id}`: the concrete read path for "admins can see it". Same-org members get the base DTO; cross-org lookups return 404 (no id-enumeration oracle); unauthenticated returns 401.
   - `PATCH /users/{user_id}` reworked — required for the new field's integrity, not gratuitous: the old handler mass-assigned arbitrary body keys into SQL (column-name injection + server-owned-field forgery), which would have let any caller set their own `last_login_ip` or `role`. Now: writable-field allowlist `{name, email}` (422 otherwise), string-value validation, object authz (self or same-org admin; cross-org 404, same-org non-admin 403), response via the same DTO.

5. **`tests/test_app.py`** — 9 new tests: IP capture, admin sees field, member does not (omitted), cross-org GET/PATCH denial, unauthenticated 401, `last_login_ip` forgery rejected with DB unchanged, `role` escalation rejected, PATCH response gating.

## Proof

- `uv run pytest -q` → **16 passed** (7 pre-existing + 9 new), 0 failures.
- Migration dry run on throwaway DB: up adds the column, documented rollback (`DROP COLUMN`) removes it — verified on SQLite 3.53.0. Per skill rule: this is a SQLite dry run, not production-like; on Postgres this exact DDL (add nullable column, no default) is metadata-only, but a prod-like rehearsal is still the standard if the engine differs.

## Contract note

Additive change only: existing consumers see identical responses unless the caller is a same-org admin, who gains the `last_login_ip` key. `null` means "user has not authenticated since the migration". No OpenAPI spec exists in the repo to diff (residual risk stated per skill).

## Residual risks / next hardening steps (pre-existing, out of scope, flagged)

- `GET /projects/search` has SQL injection via f-string interpolation of `q` and `org_id` (`app/main.py:39-46`) — P0-adjacent, untouched by this change.
- `GET /projects/{project_id}` has no org check (IDOR, `app/main.py:49-58`).
- `pay_invoice` holds a transaction across the external provider call; webhook swallows all exceptions.
- Seeded users all share the TestClient IP in tests; multi-IP behavior is exercised only via the "write only on change" branch.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/migrations/001_init.sql
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/tests/test_app.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/tests/conftest.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/011-python-fastapi/pyproject.toml
````
