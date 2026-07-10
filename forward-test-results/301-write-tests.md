# forward-test 301: write-tests (round 3)

> Round 3 (2026-07-10): targeted regression round for the round-2 miss
> (test-writing without testing-verification.md). Fresh leak-stripped copies,
> judges verified explicit ROUND-3 FOCUS items and independently reproduced
> the tested agents' cited proof.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4
Regression closed: True
Generic advice: False
Verifier quality (judge): Strong. Differential proof: new tests run against original handlers first (6 failed, exactly the injection/wildcard/role/id-orgId/400/empty-body cases), then full suite + typecheck post-fix; grader reproduced pnpm test (3 files, 27 passed) and pnpm typecheck (clean). Residual risks honestly stated per the testing reference: in-memory fake DB cannot prove real SQL/LIKE-escaping semantics, no OpenAPI so no contract diff, no pagination/q-length cap flagged as P2. Fixes verified present in src/app.ts with defense-in-depth (additionalProperties:false schema plus handler allowlist plus explicit DTO; parameterized tenant filter plus app-level literal matching with the non-escaping bind() rationale).

## Prompt

```text
We have almost no test coverage. Write tests for the project search endpoint and the user update endpoint.
```

## Round-3 focus verdict

FOCUS 1 (testing-verification.md in Files read): PASS — listed and demonstrably applied (proof matrix rows, residual-risk pattern, in-memory-DB and missing-contract-check caveats come straight from the reference). FOCUS 2 (beyond happy path): PASS — 401/404/400, two-sided cross-tenant denial with target-untouched assertion, boundary cases (empty q, wildcards-as-literals, empty-body no-op), DTO pinning. FOCUS 3 (surface SQL interpolation + Object.assign mass assignment): PASS — both surfaced with card-style severity framing (P0 mass assignment, P1 SQL injection), fixed, with a pre-fix differential run (6 failures against original handlers) proving the tests catch the planted bugs.

## References loaded

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- references/testing-verification.md
- references/auth-tenancy-security.md
- references/api-contracts.md

## Judge summary

Round-3 regression is closed: all three FOCUS items passed — testing-verification.md appears in Files read and was demonstrably applied (proof-matrix coverage, reference-pattern residual risks), the 20 new tests go well beyond happy path, and both in-scope planted flaws (P0 mass assignment, P1 SQL string interpolation) were surfaced with card-style framing, fixed safely, and proven via a pre-fix differential run. Grader independently reproduced all cited proof (27/27 pnpm test, clean typecheck) and verified the fixes in src/app.ts. Score 4: non-obvious failure modes (LIKE-wildcard literalness, non-escaping fake-driver bind()) plus defense-in-depth implementation plus inspected proof. One real miss remains: persistence-migrations.md was not loaded even though the SQL routing row fired — the same gap-class as Round 2 on a row without a proof-contract backstop — so two concrete skill edits are proposed to generalize the hard-gate fix.

## Misses

- references/persistence-migrations.md absent from Files read despite the SQL routing row ('fixing SQL injection / parameterizing queries') unambiguously firing — same failure class as the Round 2 regression, shifted to a routing row that has no Final-proof-contract backstop
- Minor (out of task scope): agent read all of src/app.ts but did not mention in passing the other planted flaws it scrolled past (floating auditLog.record promise and 'as any' body at POST /projects, readFileSync in the export handler)

## Changes needed

- SKILL.md Final proof contract: add a parallel hard gate mirroring the testing one — 'If the change adds, fixes, or parameterizes SQL/query construction, references/persistence-migrations.md must appear in the files you read.' The Round-3 fix proved hard gates work where routing-table matching alone does not; the SQL row currently has no such backstop and this run missed it.
- SKILL.md routing section: add a pre-report self-check line — 'Before the final response, re-scan the actual diff against the routing table; every row the diff matches must have its reference in files-read.' This closes the whole failure class (row fires during implementation of a fix discovered mid-task, after the initial Impact Read already chose references) instead of patching one row per round.

## Tested agent answer (verbatim)

````text
All 27 tests pass across 3 files and `tsc --noEmit` is clean.

## What was done

**New tests** (the deliverable):
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/test/projects-search.test.ts` — 10 tests for `GET /projects/search`: 401 for missing/unknown principal, substring and case-insensitive match, empty/missing `q` returns caller-org projects only, no-match returns 200 + `[]`, two-sided cross-tenant denial (org1 caller cannot see org2's project; org2 caller can), SQL-injection payloads treated as literal text, LIKE wildcards (`%`, `_`) treated as literal characters, response field-set pinned.
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/test/users-update.test.ts` — 10 tests for `PATCH /users/:id`: 401, cross-tenant 404 (target left untouched), nonexistent-id 404, name/email update + persistence, server-owned `role` cannot be set from the body (privilege-escalation regression), `id`/`orgId` cannot be set (tenant-hop regression), invalid value rejected with 400, response is exactly the 5-field DTO, empty body is a no-op. Files are separate so Vitest per-file isolation gives each a fresh in-memory store.

**Findings the tests exposed, then fixed** in `src/app.ts` (writing tests that pin a P0 as expected behavior was not acceptable):
1. P0 mass assignment (was `Object.assign(user, req.body)` onto a live DB row): body could set `role: 'admin'` (self-promotion), `orgId` (tenant hop), `id`. Fixed with a Fastify body schema (`additionalProperties: false`, typed `name`/`email`) plus a handler-level allowlist and an explicit response DTO.
2. P1 SQL injection pattern (was `` `... name LIKE '%${q}%'` `` string interpolation): payload `%' AND status LIKE '%active` observably widened the match even in the fake DB. Fixed by parameterizing the tenant filter and matching `q` in application code as a literal case-insensitive substring (the fake driver's `bind()` does not escape quotes, so pushing user text into any SQL string remains unsafe).

## Proof

- Pre-fix run of the new tests against the original handlers: `Tests 6 failed | 14 passed` — failures were exactly the injection-literal, wildcard-literal, role, id/orgId, validation-400, and (cascading) empty-body tests, proving the tests catch the real bugs.
- Post-fix: `pnpm test` → `Test Files 3 passed, Tests 27 passed (27)` including the pre-existing `test/app.test.ts` (no behavior regression on the other routes); `pnpm typecheck` → clean.

## Assumptions and residual risks

- Assumed contract: any authenticated user may update users in their own org (no role policy exists yet); forbidden fields are silently stripped (200) rather than 400, matching Fastify's default `removeAdditional` — the handler allowlist makes the invariant hold even if AJV config changes.
- Residual: no OpenAPI spec exists, so there is no contract-diff check; the fake in-memory DB cannot prove real SQL semantics (a real driver + parameterized `LIKE` with escaped `%`/`_` would be the production-grade fix); `/projects/search` has no pagination or `q` length cap (fine for the seeded fixture, a P2 if the table grows).

## Files read

- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/src/app.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/src/db.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/src/auditLog.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/test/app.test.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/package.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/301-ts-fastify/vitest.config.ts
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (via skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
````
