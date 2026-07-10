# forward-test 013: validation-library-decision

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Reproduced the P0 mass-assignment at HTTP 200 with a concrete tamper payload, verified the fix (schema drops tamper fields / returns 400) via app.inject, ran vitest (17/17) and tsc --noEmit clean, and prescribed the exact negative-path contract tests to add. Verifier matches the changed behavior at the boundary.

## Prompt

```text
We have a TypeScript API where handlers manually check request bodies with if statements. Recommend whether to keep that or introduce a validation library.
```

## References loaded (from agent's 'Files read')

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md

## Judge summary

Exemplary answer. It ran an explicit Impact Read before any language advice, loaded the correct reference (library-decisions.md, plus api-contracts.md), and applied the dependency gate to correctly recommend AGAINST a new library: extend Fastify's already-present JSON Schema validation, with Zod/TypeBox gated behind a concrete tradeoff and wired through a type provider at the boundary. It found the non-obvious failure mode the naive framing misses — Object.assign(user, req.body) lets the body overwrite orgId/id/role, a simultaneous tenant leak and privilege escalation — reproduced it at HTTP 200, proposed a safe fix (additionalProperties:false allowlist mirroring the clean transactions route), and proved it with app.inject negative-path runs plus vitest 17/17 and clean tsc. Failure removed, integration boundary, verifier, and escape hatch are all explicitly stated. Line citations are accurate to the actual source. Correctly scoped to the validation question rather than dumping all five planted flaws.

## Misses

- none

## Changes needed in skill/reference/failure card

- none

## Tested agent answer (verbatim)

````text
## Recommendation: TS Fastify request validation

**Verdict: stop hand-rolling body checks, but you do not need a third-party validation library. Standardize on Fastify's built-in JSON Schema validation — which this repo already uses correctly on one route — and extend it to every mutating endpoint.** Reach for Zod/TypeBox only if the team wants TypeScript-first schemas as a single source of truth, and even then wire it through a Fastify type provider so validation runs at the boundary, not as manual `if`/`.parse()` calls inside handlers.

This isn't a stylistic toss-up. The manual approach in this codebase has a **live P0**, which I reproduced.

### Impact Read (why this is not "none")
- **Contracts:** request bodies of `PATCH /users/:id` and `POST /projects` are unvalidated.
- **Data written:** ad-hoc handling writes arbitrary attacker-controlled fields into the store.
- **Tenant/principal boundary:** `PATCH /users/:id` lets the body overwrite `orgId`, `id`, and `role`.
- **Tests proving surface:** only happy-path; there are no negative/tamper tests on the manual routes.

Non-empty on 4 of 5 → findings-first.

### Findings (observed, not theoretical)

**P0 — `api-mass-assignment`, `src/app.ts:33`** (`PATCH /users/:id`)
`Object.assign(user, req.body)` with no schema. I injected `{role:'admin', orgId:'org2', id:'u999'}` against `x-user-id: u1` and the persisted row became `{"id":"u999","orgId":"org2","role":"admin",...}`. That is simultaneous privilege escalation and a cross-tenant move — the exact boundary `authContext()` is designed to protect, defeated through the body. Returns `200`.

**P2 — unvalidated create, `src/app.ts:57`** (`POST /projects`)
`const body = req.body as any` (`ts-any-at-boundary`). Observed:
- `{}` → `201`, project persisted with `name: undefined`.
- `{name:{$gt:''}, status:12345}` → `201`, junk types persisted verbatim.
No required-field or type enforcement; `any` erases the one signal TypeScript could give.

**Contrast — the correct in-repo pattern, `src/app.ts:93-130`** (`POST /transactions`)
This route already declares a Fastify `schema` (`required`, `type`, `enum`, `additionalProperties:false`). I injected `{amount:-5, currency:'GBP'}` → `400 FST_ERR_VALIDATION` before the handler ran. The good pattern already exists in the file; two routes just don't use it.

### Why extend Fastify schemas rather than add a library (dependency gate, `library-decisions.md`)
1. **What already solves this?** Fastify ships AJV JSON Schema validation; `library-decisions.md` names it the default for Fastify APIs, and `POST /transactions` proves it works here.
2. **What fragile code does a new lib remove?** None that Fastify schemas don't already remove. Adding Zod to call `.parse()` inside handlers reproduces the scattered-`if` problem and bypasses Fastify's schema-driven serialization.
3. **Docs current?** Not needed — no new dependency. Lockfile: `fastify@5.10.0`, already installed.
4. **Integration boundary:** the route's `schema` option — validation runs before the handler, one consistent place.
5. **Failure mode of a new lib:** validation drifting out of the boundary into ad-hoc handler code — the current bug.
6. **Verifier:** negative-path `app.inject` tests (below).

Adopt Zod/TypeBox **only** if you want one TS type + validator artifact per DTO. Then integrate via `@fastify/type-provider-typebox` or a Zod type provider so Fastify still validates at the boundary and infers `req.body` — never manual `schema.parse(req.body)` in the handler.

### Concrete fix (no new dependency) — verified working
Give the two routes the same treatment `POST /transactions` already has. Allowlist mutable fields on the user patch (`additionalProperties:false` keeps `id/orgId/role` out); require and type the project body.

I ran a Fastify app with these exact schemas via `app.inject`:
- `PATCH /users/:id` `{role,orgId,id}` → tamper fields dropped, never reach the handler (`applied:{}`); `{name:'...'}` still applies.
- `POST /projects` `{}` → `400` (`required property 'name'`); `{name:{...},status:12345}` → `400` (`name must be string`); `{name:'Delta'}` → `201`.

Additional hardening the schema switch enables for free: remove `body as any` (drop the `ts-any-at-boundary`), and give the `PATCH` route a typed `Body` so the response is an explicit DTO rather than a spread of a live ORM row (`api-bopla-property-leak` risk).

### Proof
- `npx vitest run` → 17/17 passing (baseline intact).
- `npx tsc --noEmit` → clean.
- Defect reproduction and fix verification: `app.inject` runs above (P0 mass-assignment reproduced at `200`; recommended schemas return `400`/drop tamper fields).

### First verifier to add before relying on this
Negative-path contract tests the current happy-path suite lacks: tamper `PATCH /users/:id` asserting `orgId/id/role` unchanged and unknown fields rejected; `POST /projects` asserting `400` on missing/mis-typed `name`. These lock the boundary so a future refactor can't silently reintroduce the P0.

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/package.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/db.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/auditLog.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/server.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/csv.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/app.test.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/csv.test.ts
````
