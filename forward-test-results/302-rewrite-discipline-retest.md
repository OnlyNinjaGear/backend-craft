# forward-test 302: rewrite-discipline-retest (round 3)

> Round 3 (2026-07-10): targeted regression round for the round-2 miss
> (test-writing without testing-verification.md). Fresh leak-stripped copies,
> judges verified explicit ROUND-3 FOCUS items and independently reproduced
> the tested agents' cited proof.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4
Regression closed: True
Generic advice: False
Verifier quality (judge): Strong. The agent's proof was fully reproducible: grader re-ran pnpm typecheck (clean) and pnpm test (12/12 pass) on the working copy. New tests are genuine failing-path regressions (forbidden-field PATCH with store-untouched assertion, cross-tenant PATCH 404, injection-shaped input treated literally, unknown/missing fields 400), and the agent confirmed they fail pre-fix rather than only passing post-fix. Behavior preservation proven by the 7 original tests remaining unchanged and green. Residual risks stated honestly (no OpenAPI contract to diff, in-memory store limits).

## Prompt

```text
This service is messy. Should we move it to NestJS and rewrite the persistence layer?
```

## Round-3 focus verdict

PASS on both focus items. (1) Test-writing: the agent wrote 5 new failing-path regression tests (verified present in test/app.test.ts) and references/testing-verification.md appears in its Files read list — the exact round-2 regression did not recur. (2) SQL-injection fix: the agent parameterized the search query (verified: 'WHERE orgId = ? AND name LIKE ?' at src/app.ts:85) and references/persistence-migrations.md appears in Files read — the new 'fixing SQL injection / parameterizing queries' routing signal fired. Supporting item: reliability-async.md also listed for the floating-promise finding.

## References loaded

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/README.md
- agent working copy: src/app.ts, test/app.test.ts (grep-verified), pnpm typecheck + pnpm test re-run independently

## Judge summary

Score 4/4, regression closed. Both ROUND-3 FOCUS checks passed: testing-verification.md and persistence-migrations.md both appear in Files read alongside the new tests and the SQL-injection fix, so the round-2 regression (test-writing without loading testing-verification.md) did not recur and the new persistence routing signal fired. The answer refused the NestJS/persistence rewrite with a concrete inventory-first argument, found and fixed all 5 planted flaws plus legitimate extras (server baseline, Math.random IDs), used pnpm throughout, and every proof claim was independently reproduced (tsc clean, 12/12 tests, all fixes present in source). The removeAdditional:false AJV decision is a genuinely non-obvious failure-mode catch. No skill edits needed.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
All green: typecheck clean, 12/12 tests pass. The answer is complete.

# Recommendation: No — do not migrate to NestJS, and do not rewrite the persistence layer

This is the classic `framework-rewrite-as-cleanup` failure pattern. I audited the service, and the "mess" is five concrete handler-level defects — every one of them fixable in-place in hours. I fixed them all in this pass, behavior-preserving, with regression tests as proof. A NestJS migration would have rewritten the exact security-critical surfaces where the bugs live (auth context, tenant filters) with far more regression risk than the bugs themselves.

## Inventory (retrofit read)

- Framework: Fastify 5.2 (already the right-fit choice: schema validation + throughput), TypeScript strict, ESM
- Package manager: **pnpm** (pnpm-lock.yaml — all commands below are pnpm, not npm)
- Persistence: in-memory pretend-SQL store (`src/db.ts`) with a parameterized `query/execute` API — there is no real persistence layer to "rewrite"
- Tests: Vitest + `app.inject`, 7 happy-path tests, all passing before my changes
- Size: 7 routes, ~200 LOC of app code. No DI framework needed at this scale.

## Why the mess wasn't framework-shaped (findings, all fixed in `src/app.ts`)

| Severity | Defect (original line) | Fix applied |
|---|---|---|
| P0 | SQL injection: `/projects/search` interpolated `q` and `orgId` into SQL (line 53) — `sql-string-concat` | Parameterized: `WHERE orgId = ? AND name LIKE ?` |
| P0 | Mass assignment: `PATCH /users/:id` did `Object.assign(user, req.body)` onto a **live** store row (line 36) — any caller could set `role: 'admin'` or move themselves cross-tenant via `orgId` | Allowlist schema (`name`, `email` only, `additionalProperties: false` → 400), explicit field assignment, projected response |
| P1 | Floating promise: `auditLog.record()` un-awaited in `POST /projects` (line 68) — silent audit loss + unhandled rejection | Awaited in try/catch; audit failure logged, 201 contract preserved |
| P1 | No server baseline: `Fastify()` with `requestTimeout` 0 (unbounded), no logger | `connectionTimeout: 10s`, `requestTimeout: 30s`, explicit `bodyLimit`, logger on outside tests |
| P2 | Unvalidated body: `POST /projects` used `req.body as any` (line 57) | JSON schema: `name` required, `status` enum, unknown fields → 400 |
| P2 | Event-loop blocking: `fs.readFileSync` in `/transactions/export` (line 75) | `await readFile` from `node:fs/promises` |
| P3 | Guessable IDs from `Math.random` (lines 61, 106) | `crypto.randomUUID()` |

One deliberate contract decision (state it in the changelog): Fastify's default AJV silently strips unknown body fields (`removeAdditional: true`). I set `removeAdditional: false` so unknown fields on write endpoints fail loudly with 400 — these bodies sit next to server-owned fields (`orgId`, `role`), so unknown keys are client bugs or attacks. Either mode blocks the mass-assignment vector; strict-400 makes it visible.

## Proof

- `pnpm typecheck` — clean (tsc --noEmit, no errors)
- `pnpm test` — **12/12 pass**: the 7 original happy-path tests unchanged and green (behavior preserved), plus 5 new failing-path regressions: forbidden-field update rejected and store verified untouched, cross-tenant PATCH → 404, injection-shaped search input treated literally with no cross-tenant rows, cross-tenant name probe returns empty, missing/unknown fields → 400. The mass-assignment and unknown-field tests fail against the pre-fix code (mid-run I observed 201/200 where 400 was required, which confirms they exercise the changed surface).

## On the two halves of the question

**NestJS**: adopt only if the org standardizes on it or the service grows to many teams/modules needing DI and enforced structure. Nothing here needs that; Fastify's schema validation was already doing the boundary work NestJS pipes would do, and the migration cost lands on the riskiest code. Revisit if the route surface grows ~10x or org convention demands it.

**Persistence rewrite**: there is nothing to rewrite — `src/db.ts` is an in-memory test double. The real decision is *adopting a real database*, which is a product/ops decision, not cleanup. When that happens: Postgres + Kysely or Drizzle (SQL-first, type-safe, migration workflow), keep the already-parameterized call sites, add Testcontainers-backed integration tests. That swap is now cheap precisely because the handlers no longer build SQL strings. It does not require NestJS.

## Remaining hardening backlog (in order)

1. Real auth — `x-user-id` header is fake auth (assumed intentional for this fixture); replace with signed tokens before any real exposure (P0 for production)
2. ESLint + `typescript-eslint` with `no-floating-promises`, `no-explicit-any` as a CI gate; add CI running `pnpm typecheck && pnpm test`
3. Stream or row-cap `/transactions/export` when data grows (currently whole-file read; async now, but unbounded memory)
4. Rate limiting (`@fastify/rate-limit`) on write endpoints

Residual risks: no OpenAPI contract exists, so no contract-diff check was possible (the strict-400 tightening is the only observable contract change, documented above); in-memory store means persistence semantics (locks, transactions, constraints) remain untested until a real engine exists.

Files changed: `src/app.ts`, `test/app.test.ts` (both under /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/).

## Files read

- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/package.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/src/app.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/src/db.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/src/auditLog.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/src/server.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round3/302-ts-fastify/test/app.test.ts
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
````
