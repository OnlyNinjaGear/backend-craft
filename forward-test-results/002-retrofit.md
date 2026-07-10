# forward-test 002: retrofit

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see ../docs/FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Baseline established by actually running and inspecting project commands (tsc --noEmit clean, vitest 7/7 pass), each finding paired with a concrete failing-path verifier (forbidden-field test for role/orgId escalation, injection/cross-tenant test for search, missing-name-400 for POST /projects, lint no-floating-promises), each plan stage has an exit criterion including Stage 0's proof-the-gap check that new lint flags app.ts:60 and app.ts:68, and residual risk (no contract artifact, in-memory store limits SQL/lock proofs) is stated explicitly. Only weakness: verify commands use npm instead of pnpm.

## Prompt

```text
This backend already exists. Do not rewrite it. Inspect it and produce a staged hardening plan for the next 2 weeks.
```

## References loaded (from agent's 'Files read')

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md

## Judge summary

Near-exemplary retrofit audit: complete inventory, all 5 planted flaws caught with correct card ids, file:line, fix shapes, and failing-path verifiers; correct P0/P1/P2 blast-radius routing; correct reference loading (codebase-fit first, then all seven matching risk refs, skipping start-mode refs); real baseline proof (typecheck clean, 7/7 tests, output inspected); found non-obvious amplifiers (live-row references making mass assignment persistent, tsc-blind gate closed by Stage 0 type-aware lint); no rewrite recommended and no false positives on clean contrast code. Sole blemish: verify commands say npm instead of pnpm despite the inventory correctly identifying pnpm. Note: the fixture working tree has drifted from its README (export flaw since fixed, 4 PLANTED markers remain), so grading used the README's flaw table as ground truth, which the answer matches exactly.

## Misses

- Verify commands written as 'npm run typecheck' / 'npm test' / 'npm run lint' instead of pnpm-prefixed commands, despite the agent's own inventory identifying pnpm from pnpm-lock.yaml (README prescribes 'pnpm install && pnpm test'; 'npm install' here would create a stray package-lock.json)

## Changes needed in skill/reference/failure card

- In references/codebase-fit.md (inventory section), add a hard rule: 'Verify commands MUST use the package manager detected from the lockfile (pnpm-lock.yaml -> pnpm, yarn.lock -> yarn, package-lock.json -> npm). Writing npm commands into a pnpm repo is a defect: npm install creates a conflicting lockfile.'
- In SKILL.md Retrofit mode deliverables, change 'project-local commands to verify future work' to 'project-local commands using the detected package manager (e.g. pnpm test, not npm test, when pnpm-lock.yaml exists)'

## Tested agent answer (verbatim)

````text
## backend-craft — Retrofit/Harden audit: `ts-fastify`

Mode: **Retrofit** (attach to existing backend, preserve behavior, produce staged plan) with **Harden**-style findings. I did not rewrite anything. Baseline established before planning:

- `npm run typecheck` → clean (tsc --noEmit, no errors)
- `npm test` → **7/7 pass** (vitest 3.2.7, `test/app.test.ts`)

Key baseline insight that shapes the plan: **the current gate is green but blind.** `tsc` does *not* flag the floating promise at `app.ts:68` or the `req.body as any` at `app.ts:60` (floating-promise detection is type-aware-lint only; explicit `any` is legal TS). Happy-path tests pass *by design* — the planted flaws don't break the happy path. So "green" today does not mean safe, and Stage 0 of the plan closes that visibility gap before touching behavior.

---

### Inventory

| Dimension | Finding |
|---|---|
| Framework / entrypoints | Fastify 5. `src/server.ts` (listen), `src/app.ts` (`buildApp()` — all routes) |
| Language / config | TypeScript 5.7, ESM, `target ES2022`, `strict: true`, `noEmit` |
| Runtime / pkg mgr | `tsx` (dev), Node 22 types, **pnpm** (`pnpm-lock.yaml`) |
| DB / migrations | In-memory pretend-SQL store `src/db.ts`; **no real driver, no migration system** |
| Side-effect sink | `src/auditLog.ts` — genuinely async `record()` |
| Tests | Vitest, **happy-path only** (`test/app.test.ts`), via `app.inject` |
| Lint | **none** (no eslint config, no `lint` script) |
| CI | **none** (no `.github/`) |

Notable infra amplifier: `db.query()` returns **live row references** (documented at `db.ts:53-54`), so any handler that mutates a returned row mutates the store. This turns the mass-assignment bug below from "bad response shape" into "persistent privilege escalation."

---

### Findings — ordered by blast radius

**P0 — `PATCH /users/:id` mass assignment → persistent privilege escalation + tenant hop** — `app.ts:36`
`Object.assign(user, req.body)` with `Body: Record<string, unknown>` and no schema. `user` is a live store row (`db.ts:53`). A caller can send `{"role":"admin"}`, `{"orgId":"org2"}`, `{"id":...}`, `{"email":...}` and the write **persists**. The read is correctly tenant-scoped (`SELECT ... WHERE id=? AND orgId=?`) but the mutation is uncontrolled. Also returns the mutated model directly (property leak). Cards: `api-mass-assignment`, `api-bopla-property-leak`.
Fix shape: body JSON schema with `additionalProperties:false` allowlisting only writeable fields (e.g. `name`); assign field-by-field into a copy; never `Object.assign` the request body; return an explicit DTO. Set `role`/`orgId`/`id`/`email` server-side only.
Verifier: forbidden-field test — PATCH with `role:"admin"` / `orgId:"org2"` must not change stored role/org (assert 400 or ignored).

**P0 — `GET /projects/search` SQL built by string concatenation** — `app.ts:53`
`` `SELECT * FROM projects WHERE orgId = '${ctx.orgId}' AND name LIKE '%${q}%'` `` interpolates user-controlled `q` directly. Card: `sql-string-concat`. Against a real Postgres/MySQL this is classic injection and a cross-tenant read/exfil vector; against the toy parser the exact exploit is store-specific, but the pattern is P0 and must not survive into any real driver.
Fix shape: parameterize — `db.query('SELECT ... WHERE orgId = ? AND name LIKE ?', [ctx.orgId, '%' + q + '%'])` (the codebase already does this everywhere else). Add explicit projection while here (see P2 SELECT *).
Verifier: injection/tenant test — a crafted `q` cannot return another org's project; parameterized query still matches `Apol`→`Apollo`.

**P0-if-deployed (by-design stub) — header-trust "auth"** — `app.ts:10-17`
`authContext` trusts `x-user-id` verbatim; anyone can impersonate any user and cross any tenant by setting a header. The comment marks it "Fake auth," so I treat it as intentional scaffolding — but it is the single gating item before this service faces untrusted traffic. Assumption: real deployment requires replacing this with verified authn (signed JWT/session) behind the *same* `authContext` interface, keeping tenant derived server-side. Scheduled as Stage 9.

**P1 — floating promise drops audit event / can crash process** — `app.ts:68`
`auditLog.record('project.created', ...)` is not awaited/void/caught; `record()` returns a real Promise (`auditLog.ts:5`). Unhandled rejection can terminate the Node process; audit loss is silent. Contrast `app.ts:115` which awaits correctly. Card: `ts-floating-promise`.
Fix shape: `await` inside the handler's try/catch (mirror `/transactions`).
Verifier: type-aware ESLint `no-floating-promises` clean + test that project creation still returns 201.

**P1 — `POST /projects` unvalidated body via `as any`** — `app.ts:57-60`
No Fastify schema; `req.body as any`; `body.name` can be missing/wrong type and is inserted and echoed back. Cards: `ts-any-at-boundary`, contract drift. Contrast `/transactions` which has `createTransactionSchema`.
Fix shape: add a JSON schema mirroring `createTransactionSchema` (`required:['name']`, `additionalProperties:false`, optional `status` enum); type the body from the schema; drop `as any`.
Verifier: validation test — `POST /projects` with missing `name` → 400.

**P1 — synchronous file read blocks the event loop** — `app.ts:75`
`fs.readFileSync(...)` on the request path in `GET /transactions/export`; plus full in-memory line split/filter. Blocks *all* concurrent requests for the duration; degrades as the CSV grows. Card: `event-loop-blocking`.
Fix shape: `await fs.promises.readFile(...)` now; stream + line-filter for the real fix. Preserve the org filter.
Verifier: async read keeps the export test green; event-loop-delay note for load.

**P2 — `SELECT *` / persistence models on public responses** — `app.ts:44-46, 53-54, 37`
`/projects/:id`, `/projects/search`, and `PATCH /users/:id` return whole rows. Today the leak is bounded (few columns), but any future column (secret flag, internal status) auto-leaks. `/users` list (`app.ts:26`) already does this right with an explicit projection — follow that pattern. Cards: `select-star-public-response`, `api-bopla-property-leak`.
Fix + verifier: explicit column projection + response schema; test asserts forbidden fields absent.

**P2 — no pagination on growable collections** — `app.ts:26` (`/users`), `app.ts:53` (`/projects/search`). Adding it later breaks array-expecting consumers. Card: `api-pagination-late`. Add `limit` + cursor with a max cap now; test max page size and stable ordering.

**P2 — mutations lack idempotency keys** — `POST /transactions` (`app.ts:98`), `POST /projects` (`app.ts:57`). Random IDs mean a client retry after a timeout creates duplicates — meaningful for transactions (money). Card: `api-idempotency-missing-on-mutation-retry`. Add idempotency-key header + dedupe; test duplicate request → one side effect.

**P2 — observability / ops baseline missing.** `Fastify()` constructed with no logger, no surfaced request/correlation id, no `/health`; `req.log.error` at `app.ts:117` currently goes nowhere. `server.ts` has no SIGTERM/SIGINT → `app.close()` (in-flight requests dropped on deploy), and no `requestTimeout`/`connectionTimeout`. Cards: `observability-no-correlation-id`. Enable logger + reqId, add `/health`, add graceful shutdown + timeouts.

**P2 — error contract drift + no global handler.** Ad hoc `{error:'...'}` per handler; schema-validation 400s use Fastify's default shape (different from handlers'); no `setErrorHandler`, no stable codes, unhandled 500s can leak default detail. Card: `api-error-contract-drift`. Add `setErrorHandler` with stable code + correlation id, no stack in prod.

**P2 (enabling) — no lint, no CI.** The two P1 TypeScript bugs are invisible to `tsc`; only type-aware `@typescript-eslint` (`no-floating-promises`, `no-explicit-any`) catches them, and nothing runs on push. This is the meta-gap — fix it first so every later stage is provable and stays fixed.

---

### Staged 2-week hardening plan

Principle: each stage ships independently, keeps the 7 existing tests green (behavior preserved), and adds the **failing-path** test for the surface it fixes. Verify after every stage with `npm run typecheck && npm run lint && npm test`.

**Week 1 — visibility + stop the bleeding (P0/P1)**

- **Stage 0 — Day 1 · Guardrails (enabling).** Add `@typescript-eslint` type-aware config with `no-floating-promises` + `no-explicit-any` + `no-misused-promises`; add `"lint"` script; add minimal CI (pnpm install → typecheck → lint → test). *Exit:* lint runs and flags `app.ts:60` and `app.ts:68` (proves the gap was real). No behavior change.
- **Stage 1 — Day 2 · PATCH /users mass assignment (P0).** Body schema (allowlist `name`/`email`), field-by-field copy, no `Object.assign` of body, no mutation of the live row, explicit DTO out. *Exit:* new forbidden-field test (role/orgId cannot escalate) + 7 old tests green.
- **Stage 2 — Day 3 · /projects/search parameterize (P0).** Replace concat with bound params; explicit projection. *Exit:* injection/tenant test green.
- **Stage 3 — Day 4 · POST /projects (P1).** `await` the audit call in try/catch; add JSON schema; delete `as any`. *Exit:* missing-`name`→400 test; lint clean on this file.
- **Stage 4 — Day 5 · async export (P1).** `fs.promises.readFile` (stream as follow-up); org filter unchanged. *Exit:* export test green; note on load.

**Week 2 — contract, tenancy, and ops hardening (P2)**

- **Stage 5 — Day 6 · DTOs + response schemas.** Kill `SELECT *` on public responses across `/projects/:id`, `/projects/search`, PATCH `/users`; assert forbidden fields absent.
- **Stage 6 — Day 7 · error + observability baseline.** `setErrorHandler` with stable codes + correlation id; enable logger + surface reqId; add `/health`. Contract tests for 400/401/404/500.
- **Stage 7 — Day 8 · pagination.** `limit`+cursor with max cap and stable ordering on `/users` and `/projects/search`.
- **Stage 8 — Day 9 · idempotency + graceful ops.** Idempotency-key + dedupe for `POST /transactions` (then `/projects`); SIGTERM/SIGINT → `app.close()`; set `requestTimeout`/`connectionTimeout`. Duplicate-request and shutdown tests.
- **Stage 9 — Day 10 · auth seam + persistence plan (P0-if-deployed).** Replace header-trust `authContext` with verified-token auth behind the same interface, tenant still server-derived; forbidden-principal tests. Document the move off the in-memory store: real driver + migration tool + expand/contract discipline + statement timeouts before any destructive DDL. Buffer for review.

Project-local verify commands (existing + one to add):
- `npm run typecheck` — `tsc --noEmit`
- `npm test` — `vitest run`
- `npm run lint` — **to add in Stage 0** (type-aware ESLint; this is what actually catches the two P1 TS defects)

Residual risk to state plainly: no OpenAPI/Pact contract artifact exists, so public-contract changes in Weeks 1–2 are only guarded by response-schema tests you add, not by a consumer contract check; and persistence semantics (locks, real SQL injection behavior, transactions) cannot be proven against the in-memory `db.ts` — those proofs move to a real engine at Stage 9.

---

### Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/server.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/db.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/auditLog.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/package.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/tsconfig.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/vitest.config.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/app.test.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/data/transactions.csv
````
