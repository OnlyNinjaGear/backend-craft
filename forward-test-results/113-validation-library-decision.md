# forward-test 113: validation-library-decision (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong: matches library-decisions.md's prescribed 'invalid input tests' verifier exactly — 7 new invalid-input tests including a mass-assignment regression proof (protected fields unchanged after hostile PATCH), pnpm typecheck pass, pnpm test 14/14 with pre-existing happy-path tests preserved, plus an empirical runtime probe demonstrating Ajv's removeAdditional stripping behavior. Output was inspected, not just run.

## Prompt

```text

```

## Round-2 focus verdict

loads library-decisions.md: PASS (read and structurally applied). names Fastify stack fit before recommending: PASS (headline recommendation anchored on existing in-repo Fastify schema route). tradeoffs: PASS (manual checks and Zod/Valibot rejected with codebase-specific reasons, future trigger named). failure removed: PASS (api-mass-assignment card + validation drift). integration boundary: PASS (per-route JSON-schema at route registration + handler allowlist). verifier: PASS (invalid-input tests, typecheck, runtime probe, all inspected). escape hatch: PASS (removal path + conditions for adopting a library later).

## References loaded

- SKILL.md
- references/library-decisions.md
- references/api-contracts.md
- references/codebase-fit.md
- references/language-adapters.md

## Judge summary

Score 4/4. The agent loaded library-decisions.md and executed its Dependency gate end-to-end: named the Fastify stack fit first (built-in Ajv route schemas already in use at POST /transactions, zero new deps), gave concrete alternative tradeoffs (manual checks, Zod/Valibot, TypeBox later-trigger), named the removed failure (api-mass-assignment card), stated the integration boundary (per-route schemas + handler allowlist), supplied strong verifiers (7 invalid-input tests incl. mass-assignment proof, typecheck, 14/14 tests, hostile runtime probe), and gave an escape hatch/removal path. It also found all 5 planted fixture flaws, correctly scoped SQL injection as not fixed by validation, and empirically proved the non-obvious Ajv removeAdditional silent-strip failure mode with defense in depth. Only nits: auth-tenancy-security.md and testing-verification.md were not loaded despite matching routing signals, with no substantive consequence. All round-2 focus items are closed.

## Misses

- Did not load references/auth-tenancy-security.md despite the tenant-boundary signal (orgId overwrite) surfaced in its own Impact Read — routing table row matched (minor; api-contracts.md covered mass-assignment and the fix is correct)
- Did not load references/testing-verification.md before prescribing the new test suite, which the retrofit rule requires (minor; delivered tests are nonetheless the right shape)

## Changes needed

- none

## Tested agent answer (verbatim)

````text
# Recommendation: drop the manual if-checks — but do NOT add a new validation library. Standardize on Fastify's built-in JSON-schema route schemas, which this codebase already uses.

## Impact Read (why this is not a style question)

- **Public contracts change**: request DTOs for 3 routes now reject/strip invalid input (400s where garbage was previously accepted).
- **Data writes at risk**: `PATCH /users/:id` did `Object.assign(user, req.body)` onto a **live** store row (`db.query` returns live references) — unvalidated body could overwrite `orgId`, `role`, `id`. That is a P0 mass-assignment / tenant-escape, not a lint nit. `POST /projects` inserted `body.name` from `req.body as any` with zero checks (missing name → literal `'undefined'` row).
- **Existing proof**: tests were happy-path only; no invalid-input coverage existed.

## Decision (dependency gate applied)

**Chosen: Fastify JSON Schema route schemas (Ajv, bundled — zero new dependencies).**

1. **Project-local tool already solves this.** `POST /transactions` (src/app.ts) already uses a route schema; Fastify 5 ships Ajv with `removeAdditional: true`, `useDefaults`, `coerceTypes`. The "library" is installed, in use, and idiomatic here.
2. **What it removes**: failure cards `api-mass-assignment` (verified fixed) and ad-hoc per-handler validation drift. Manual if-checks fail in a predictable way: every handler re-invents required/type/bounds checks, nobody writes the `additionalProperties` check by hand, and the one route someone forgets is the breach.
3. **Alternatives rejected**:
   - **Keep manual if-checks** — rejected. In this codebase "manual" degenerated to `as any` and blind `Object.assign` within 5 routes. Hand checks also can't feed Fastify's serialization or future OpenAPI generation.
   - **Zod / Valibot** — rejected *for now*. Would add a dependency and a second validation idiom next to the existing JSON-schema route, bypass Fastify's schema-aware fast-path (unless bridged via `fastify-type-provider-zod`), and buys nothing this API needs. Legitimate later trigger: if you need validated types shared with a frontend or complex cross-field rules, adopt `@fastify/type-provider-typebox` (JSON-schema-native, so it composes with what's already here) rather than Zod.
4. **Failure mode if misconfigured**: Ajv's default `removeAdditional: true` *strips* unknown fields instead of 400-ing. I verified this empirically (PATCH with `orgId`/`role` → 200, fields stripped, row untouched) and added defense in depth: the handler assigns only `name`/`email` explicitly, so the allowlist holds even if Ajv options change.
5. **Removal path**: schemas are plain JSON-schema objects per route; deleting one restores prior behavior.

## What I changed (all in the project directory)

- `src/app.ts`:
  - `PATCH /users/:id` — added body schema (allowlist `name`, `email`; `additionalProperties: false`, `minProperties: 1`) and replaced `Object.assign(user, req.body)` with explicit per-field assignment. **Fixes the mass-assignment P0.**
  - `POST /projects` — added body schema (`name` required, 1–200 chars; `status` enum `active|archived`), removed `req.body as any`, typed the route generic.
  - `GET /projects/search` — added querystring schema (`q` max 100 chars) to bound input.
- `test/app.test.ts` — new `request validation` describe block: 7 invalid-input tests including the mass-assignment proof (protected fields unchanged after hostile PATCH).

**Intentional behavior changes** (assumptions stated): missing/empty project `name` → 400 (was: inserted `undefined`); `status` outside `active|archived` → 400 (was: any string); empty PATCH body → 400; unknown PATCH fields silently stripped; search `q` capped at 100 chars.

## Proof

- `pnpm typecheck` (tsc --noEmit): **pass** (pnpm per `pnpm-lock.yaml` — do not use npm here).
- `pnpm test` (vitest): **14/14 pass** — all 7 pre-existing happy-path tests unchanged and green (behavior preserved for valid inputs), plus 7 new invalid-input tests, notably `blocks mass assignment of orgId/role/id via PATCH` and `rejects project creation without a name`.
- Runtime probe: hostile `PATCH /users/u1` with `{orgId:'org2', role:'admin'}` → `200`, response row shows `orgId:'org1'`, `role:'member'` (fields stripped).

## Findings that validation does NOT fix (do not let a schema create false confidence)

- **P0 — SQL injection**, `src/app.ts` `GET /projects/search` (~line 74 post-edit): `` db.query(`... orgId = '${ctx.orgId}' AND name LIKE '%${q}%'`) `` interpolates `q` directly. The new `maxLength: 100` schema shrinks the payload window but is not a fix — parameterize: `db.query('SELECT * FROM projects WHERE orgId = ? AND name LIKE ?', [ctx.orgId, '%' + q + '%'])`. Verifier: test that `q=%27%20OR%201=1--` returns only org-scoped name matches. (Left unfixed: out of the validation question's scope; flagging so it's not lost. Note `db.ts`'s `bind()` also doesn't escape quotes in params — toy driver, but worth knowing.)
- **P2 — floating promise**, `src/app.ts` `POST /projects`: `auditLog.record(...)` is not awaited (the `/transactions` route awaits it). Fix: `await` + the same try/catch shape. Verifier: eslint `@typescript-eslint/no-floating-promises`.
- **P2 — sync I/O + unbounded export**, `GET /transactions/export`: `fs.readFileSync` on the request path and no row cap/streaming; cost grows with the file.
- **P2 — server baseline** (retrofit rule): `buildApp()`/`server.ts` set no `requestTimeout`/`connectionTimeout` and rely on the default `bodyLimit` (1 MiB — fine, but make it explicit). Suggested: `Fastify({ requestTimeout: 30_000, bodyLimit: 1_048_576 })`.
- **P3 — follow-up worth doing**: add **response** schemas per route (BOPLA/property-leak protection + fast-json-stringify speedup) — natural next step of the same approach; today `GET /projects/:id` returns `SELECT *` rows directly.

## Files changed

- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/src/app.ts` (modified: 3 route schemas added, `as any` and `Object.assign` mass-assignment removed)
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/test/app.test.ts` (modified: added `request validation` suite, 7 tests)

## Files read

- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/src/app.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/src/db.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/src/auditLog.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/src/server.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/test/app.test.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/013-ts-fastify/package.json
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
````
