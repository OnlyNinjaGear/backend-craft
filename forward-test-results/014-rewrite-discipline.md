# forward-test 014: rewrite-discipline

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Two-layer proof: (1) current-state proof actually run and inspected -- pnpm test 17/17 and pnpm typecheck clean, both independently re-verified by the grader as accurate, with the sharp observation that a clean typecheck demonstrates why lint is needed; (2) per-finding verifiers that each match the specific defect (forbidden-field PATCH test asserting 400 plus unchanged row, injection-shaped q parameter test asserting tenant-scoped results, invalid-body 400 tests, no-floating-promises/no-explicit-any CI rules, rejecting-audit-sink test), plus migration up/down proof and Testcontainers for the future DB adoption. Satisfies the skill's final-proof contract for an advisory task where no behavior was changed.

## Prompt

```text
This service is messy. Should we move it to NestJS and rewrite the persistence layer?
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/codebase-fit.md
- references/library-decisions.md
- references/persistence-migrations.md
- references/auth-tenancy-security.md
- references/language-adapters.md

## Judge summary

Score 4. The agent correctly identified the question as the framework-rewrite-as-cleanup trap, ran a genuine impact read (inventory of Fastify 5, 17 tests, in-memory DB, tenant model) before any framework talk, and walked the library-decisions dependency gate to reject NestJS absent a product/ops reason -- allowing it later only as a mechanical port after hardening. It found all 4 flaws actually planted in the current fixture (the README's 5th, event-loop-blocking, was removed from the code; the README is stale) with correct file:line and card ids, zero false positives against the clean contrast code, and a non-obvious amplifier: db.query's live row references make the mass assignment persist. Proof claims were re-verified by the grader and are accurate. Minor misses: timeouts/body limits absent from the hardening plan, and reliability-async.md / testing-verification.md not loaded despite citing a card from the former and prescribing tests per the latter.

## Misses

- Hardening plan omits server baseline hardening named in expected behaviors: no mention of request/connection timeouts or body-size limits (marginal -- the fixture plants no timeout flaw and has no outbound calls, but the P1 'megabyte string' observation should have led to a bodyLimit recommendation)
- Did not load references/reliability-async.md despite citing the ts-floating-promise failure card, which is defined there -- the card id was apparently sourced indirectly (language-adapters.md lint list), a routing gap
- Did not load references/testing-verification.md even though the plan prescribes new tests and a CI ratchet

## Changes needed in skill/reference/failure card

- Add a routing row to SKILL.md reference table: 'fire-and-forget call, unawaited/floating promise, background side effect' -> references/reliability-async.md, so the async-side-effect signal routes there explicitly (current row only lists retry/timeout/queue/worker/cron/webhook/cancellation/external API)
- Add a 'server baseline' item to the retrofit-mode deliverables in SKILL.md (or codebase-fit.md): request timeouts, body-size limits, connection limits must appear in every staged hardening plan even when no specific flaw is found
- Add to SKILL.md retrofit/harden modes: when proposing new tests or CI gates, load references/testing-verification.md before writing the verifier plan
- Grading-infra fix (not a skill change): update /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/README.md -- it still claims 5 planted flaws (event-loop-blocking was removed and the export handler is now clean), stale line numbers (36/53/60/68 vs actual 33/50/57/65), and 7 tests vs actual 17; a future grader using the README as answer key would wrongly penalize a correct answer

## Tested agent answer (verbatim)

````text
# Should we move to NestJS and rewrite the persistence layer?

**No.** This is the `framework-rewrite-as-cleanup` trap. The "mess" is four localized handler defects in `src/app.ts` — none of which a framework migration would fix, and all of which would be carried straight into a NestJS port. Meanwhile the parts of this service that are genuinely good (tenant scoping, schema validation, CSV hardening, the test suite) are exactly what a rewrite would put at risk.

Assumptions: small single-team service (~7 routes), no org-wide NestJS mandate, the in-memory store is a stand-in for a future real database.

## Why the rewrite doesn't pass the dependency gate

1. **What does the project already have?** Fastify 5 with JSON-schema route validation, fast serialization, and built-in pino logging. Per the skill's TS defaults, Fastify is the *recommended* choice "when schema validation, serialization, and throughput matter." NestJS is justified when a team wants opinionated modules/DI for enterprise consistency — a team-structure preference, not a defect fix.
2. **What failure would NestJS remove?** None of the actual defects below. Mass assignment, SQL string concatenation, `as any` at a boundary, and a floating promise are handler-level bugs; they port verbatim into NestJS controllers.
3. **What's the failure mode of migrating?** The migration itself is the biggest risk event: every route and test rewritten, with the currently *proven* behaviors (cross-tenant isolation, 401s, schema rejection — 17 passing tests) exposed to regression for zero defect payoff.
4. **Persistence "rewrite":** there is no real persistence layer to rewrite. `src/db.ts` is an in-memory pretend-SQL store. The real decision is *when to adopt a real database*, and that's a planned adoption (below), not a cleanup rewrite.

## What's actually wrong (findings, by severity)

**P0 — mass assignment enables privilege escalation and tenant corruption**
`src/app.ts:33` — `Object.assign(user, req.body)` in `PATCH /users/:id`. Any authenticated user can set `role: 'admin'`, `orgId: 'org2'`, `id`, or `email` on a user row. Because `db.query()` returns **live row references** (`src/db.ts:53-55`), the write persists to the store. Blast radius: role escalation plus corruption of the tenant boundary itself. Failure card: `api-mass-assignment`.
Fix shape: Fastify route schema with `additionalProperties: false` allowlisting only client-writable fields (e.g. `name`); assign server-owned fields (`role`, `orgId`, `id`) server-side only, and write back an explicit copy rather than mutating the live row.
Verifier: forbidden-field test — `PATCH /users/u1` with `{ role: 'admin' }` / `{ orgId: 'org2' }` returns 400, and a subsequent `GET` proves the row is unchanged.

**P0 — SQL string concatenation on a user-controlled input**
`src/app.ts:50` — `/projects/search` builds `` `... orgId = '${ctx.orgId}' AND name LIKE '%${q}%'` `` by interpolation. With any real driver this is SQL injection: cross-tenant read/exfiltration through the search endpoint. Failure card: `sql-string-concat`. It's also the only non-parameterized query in the file — every other route does it right.
Fix shape: `db.query('SELECT * FROM projects WHERE orgId = ? AND name LIKE ?', [ctx.orgId, '%' + q + '%'])` (escape `%`/`_` in `q` when on a real driver).
Verifier: injection-shaped test (`q=' OR '1'='1`) asserting only the caller org's rows return; a semgrep/lint rule banning template literals passed to `db.query`.

**P1 — unvalidated `any` body at a public boundary**
`src/app.ts:57` — `POST /projects` casts `req.body as any` and inserts `body.name`/`body.status` with no schema. `name` can be `undefined`, an object, or a megabyte string. Failure card: `ts-any-at-boundary`. The fix already exists in the same file: copy the pattern from `POST /transactions` (`src/app.ts:93-104`) — required `name`, `status` enum, `additionalProperties: false`.
Verifier: invalid-input tests (missing `name` → 400).

**P1 — floating promise on the audit write**
`src/app.ts:65` — `auditLog.record(...)` is genuinely async (`src/auditLog.ts`) and is neither awaited nor caught in `POST /projects`; a failed audit write is silently lost after a 201, and a rejection becomes an unhandled-rejection crash risk. Failure card: `ts-floating-promise`. Again the correct pattern is three routes down: `await auditLog.record(...)` inside try/catch (`src/app.ts:123`).
Verifier: `@typescript-eslint/no-floating-promises` in CI; a test with a rejecting audit sink.

**P2 — persistence seam footguns to fix at adoption time, not by rewrite**
`src/db.ts` returns live row references and handlers embed SQL strings inline. That's acceptable for a bounded in-memory store (it's documented), but it's what turned the P0 mass assignment into a persisted write. `Math.random()`-based IDs (`src/app.ts:58,114`) are collision-prone. Neither justifies a rewrite today; both belong on the real-DB adoption checklist.

**P3 — no linter.** Adding typescript-eslint with `no-floating-promises` and `no-explicit-any` would have caught two of the four defects mechanically.

## What to preserve (why a rewrite is net-negative)

- Tenant context derived from the authenticated user, never the body (`src/app.ts:7-14`), with parameterized `(id, orgId)` scoping on reads.
- JSON-schema validation done correctly on `POST /transactions`.
- RFC-4180 CSV export with formula-injection neutralization and an explicit column allowlist (`src/csv.ts`, `src/app.ts:76-90`).
- A real test suite proving cross-tenant isolation in both directions (`test/app.test.ts:111-119`).

## Recommended plan instead of a rewrite

1. **Now (small, behavior-preserving diffs):** fix both P0s + both P1s in `src/app.ts` (~20 lines total), add forbidden-field, injection-shaped, and invalid-body tests.
2. **CI ratchet:** add typescript-eslint (`no-floating-promises`, `no-explicit-any`) alongside the existing `pnpm typecheck` and `pnpm test`.
3. **When a real database is needed (its own project, not "cleanup"):** Postgres with Kysely (SQL-first, type-safe) or Drizzle (TS schema + migrations) per the skill's TS defaults; introduce a thin repository module at the current `db.query`/`db.execute` call sites; explicit projections on public paths; migrations with up/down proof; Testcontainers-based integration tests. Prisma only if generated-client CRUD speed outweighs query control.
4. **NestJS:** revisit only if the org standardizes on it or the service grows to many modules/teams wanting enforced DI structure — and then as a mechanical port *after* the defects are fixed and covered by tests, never as the vehicle for fixing them.

## Proof (current state)

- `pnpm test`: 17/17 passing (test/app.test.ts 11, test/csv.test.ts 6) — the happy path is protected; the findings above are safety holes the happy path doesn't exercise.
- `pnpm typecheck` (`tsc --noEmit`): clean — which demonstrates the `as any` cast and floating promise are invisible to the current toolchain, hence the lint recommendation.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/package.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/db.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/csv.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/auditLog.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/server.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/app.test.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/csv.test.ts
````
