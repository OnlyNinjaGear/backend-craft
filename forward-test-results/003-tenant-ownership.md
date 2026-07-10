# forward-test 003: tenant-ownership

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Cited '.venv/bin/pytest -v, 12 passed' with output inspected; the key verifier (test_get_project_cross_tenant_is_404) is a true regression guard tied to the exact changed behavior — the agent even articulated the counterfactual (Bob would get 200 with the Acme row under the old handler). Independently re-ran pytest: all tests pass, including the five new ones. Also covered auth-required, missing-id, malformed-id, and full response-shape cases, and honestly noted no OpenAPI contract-diff tooling exists so shape is proven by test only.

## Prompt

```text
Add an endpoint to fetch a project by id for the current user.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/api-contracts.md
- references/auth-tenancy-security.md
- references/testing-verification.md
- references/language-adapters.md

## Judge summary

Full marks. All four expected behaviors hit and independently verified against the fixture: the handler at /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py:51-64 does a parameterized (id, org_id) fetch with org_id from the auth principal, and the five new tests in tests/test_app.py (cross-tenant 404, missing 404, no-auth 401, non-int 422, shape assertion) all pass (pytest run confirmed). Beyond the rubric, the agent found non-obvious failure modes: existence-leak avoidance (same 404 body for cross-tenant vs missing, matching the pay_invoice pattern), route-declaration order relative to /projects/search, 422 path-type validation, and the shadowed-route hazard of literally 'adding' a second endpoint on the same path. It also correctly declined to fix the other four planted flaws while explicitly listing them as residual risks. Proof matched changed behavior exactly and the cross-tenant test is a genuine regression guard (would fail on the old handler). No generic checklist advice; everything cited file:line, code, and test names.

## Misses

- none

## Changes needed in skill/reference/failure card

- none

## Tested agent answer (verbatim)

````text
All 12 tests pass, including the 5 new ones. The cross-tenant test is a real regression guard: against the previous handler (`WHERE id = ?` only), Bob fetching Alice's project 1 would have returned 200 with the Acme row, so `test_get_project_cross_tenant_is_404` would have failed.

## Result

**Endpoint delivered:** `GET /projects/{project_id}` in `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py` (lines 51–65).

**What changed and why:**

1. **Tenant-scoped fetch** — The route existed but was vulnerable to BOLA/id-swap: it fetched by `id` alone, so any authenticated user could read any org's project. The handler now queries by `(id, org_id)` with `org_id` derived server-side from the authenticated principal (`get_current_user`), never from client input:
   ```python
   row = conn.execute(
       "SELECT id, org_id, name, status FROM projects WHERE id = ? AND org_id = ?",
       (project_id, user["org_id"]),
   ).fetchone()
   ```
2. **No existence leak** — A cross-tenant id returns the same `404 {"detail": "project not found"}` as a missing id, matching the existing `pay_invoice` pattern in the same file.
3. **Contract discipline** — Explicit column list (`id, org_id, name, status`), same item shape as `GET /projects`; parameterized SQL (no string concatenation); `project_id: int` path typing gives 422 on malformed ids via FastAPI validation. Route declaration stays after `/projects/search`, preserving route-matching order.
4. **Tests added** in `/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py`, covering the proof matrix for a public endpoint over tenant-owned data:
   - `test_get_project_by_id` — success, full response-shape assertion
   - `test_get_project_cross_tenant_is_404` — cross-tenant denial (Bob/org 2 vs project 1/org 1)
   - `test_get_project_missing_is_404` — nonexistent id
   - `test_get_project_requires_auth` — 401 without `X-User-Id`
   - `test_get_project_non_integer_id_is_422` — path validation

**Proof:** `.venv/bin/pytest -v` — `12 passed` (7 pre-existing + 5 new), output inspected above; all new tests PASSED.

**Assumptions stated:**
- "Add an endpoint" was interpreted as delivering the correct implementation on the existing `/projects/{project_id}` path — adding a second route on the same path would conflict/shadow rather than add. The planted-flaw comment was removed since the flaw no longer exists at that site.
- 404 (not 403) for cross-tenant access, consistent with the codebase's existing invoice handler and standard existence-hiding practice.

**Residual risks (out of scope for this change, present elsewhere in the fixture):** SQL injection in `/projects/search`, mass assignment in `PATCH /users/{user_id}`, swallowed webhook exceptions, and a transaction spanning a network call in `/invoices/{invoice_id}/pay`. No OpenAPI contract-diff tooling exists in the project, so contract verification is via the response-shape test only.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/auth.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/db.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/__init__.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/migrations/001_init.sql
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/conftest.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/tests/test_app.py
- /Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/pyproject.toml
````
