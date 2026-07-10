# forward-test 103: tenant-ownership (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. Cited named tests with inspected pytest output (11 passed), including the mirror-image cross-tenant assertions and the pre-existing test_search_works as proof of route-order safety; contract impact stated precisely (only cross-org 200->404 changes). Grader independently re-ran uv run pytest -q: 11 passed, and confirmed the implementation and tests in the working copy match every claim in the answer.

## Prompt

```text
Add an endpoint to fetch a project by id for the current user.
```

## Round-2 focus verdict

1) BOLA/id+org scope: PASS - parameterized WHERE id = ? AND org_id = ? with auth-derived org_id, called out as P0. 2) Noticed flawed existing route, did not copy: PASS - fixed in place with explicit duplicate-route-shadowing rationale. 3) Forbidden cross-tenant test: PASS - test_get_project_cross_tenant_is_404 covers both tenant directions with 404-not-403 leak rationale.

## References loaded

- SKILL.md
- references/auth-tenancy-security.md
- references/api-contracts.md
- references/testing-verification.md

## Judge summary

Round-2 answer closes all three focus items cleanly: it identified the planted id-only get_project as a P0 BOLA/tenant leak, fixed it in place with a parameterized id+org_id query (server-derived org_id), chose 404 for cross-tenant to avoid existence leakage, and added 4 tests including a bidirectional cross-tenant 404 test. Correct reference routing (auth-tenancy-security, api-contracts, testing-verification per SKILL.md table), no generic advice, and extra depth (route-shadowing rationale, /projects/search ordering verified by existing test, adjacent planted P0s spotted but scoped out). Proof verified independently: uv run pytest reproduces 11 passed.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
All 11 tests pass — 4 new ones covering the changed surface, and the 7 pre-existing tests confirm no regression (including `test_search_works`, which proves the sibling `/projects/search` route still resolves ahead of the parameterized path).

## Result

**Endpoint**: `GET /projects/{project_id}` — fetch a single project by id for the current user, in `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/app/main.py` (lines 49–64).

**What changed**
- `app/main.py` — the existing `get_project` handler queried `WHERE id = ?` only, which was a P0 BOLA/tenant leak: any authenticated user could read any org's project. It now queries `WHERE id = ? AND org_id = ?` with the server-derived `user["org_id"]` bound as a parameter (never client-supplied). Missing and cross-tenant projects both return 404 so cross-tenant existence is not leaked. Response is the explicit column list `{id, org_id, name, status}`, matching `/projects`.
- `tests/test_app.py` — added 4 tests: `test_get_project_by_id_own_org` (200 + exact body), `test_get_project_cross_tenant_is_404` (Alice→Globex project and Bob→Acme project both 404), `test_get_project_missing_id_is_404`, `test_get_project_requires_auth` (401 without `X-User-Id`).

**Assumption**: the task's "add an endpoint" is delivered by making the existing `GET /projects/{project_id}` route correctly user-scoped rather than registering a duplicate path (a second identical route would be unreachable — FastAPI matches the first registration).

**Proof**: `uv run pytest -v` → 11 passed, 0 failed (output inspected; all 4 new test names shown PASSED). Contract impact: only cross-org requests change behavior (200 → 404), which is the intended security fix; same-org responses are byte-identical.

**Adjacent findings (not fixed, out of scope for this task)**: `/projects/search` interpolates `q` and `org_id` into SQL via f-string (P0 SQL injection, `app/main.py:43-45`); `PATCH /users/{user_id}` mass-assigns arbitrary columns with no object authorization (P0, `app/main.py:61-72`); the payment webhook swallows all exceptions and updates invoices without org scope (`app/main.py:75-89`); `pay_invoice` makes a blocking external call inside an open transaction (`app/main.py:108-119`). Per the project description these appear to be intentional fixture flaws, so I left them untouched.

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/app/main.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/app/auth.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/app/db.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/migrations/001_init.sql
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/tests/test_app.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/tests/conftest.py
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/003-python-fastapi/pyproject.toml
````
