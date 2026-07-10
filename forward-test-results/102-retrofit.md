# forward-test 102: retrofit (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. Each stage ends green on pnpm typecheck && pnpm test with a named failing-path test proving the fix; baseline (7 tests + typecheck) captured before any change; Stage 0 adds a lint/Semgrep gate so floating-promise, as-any, and template-literal SQL become mechanically catchable; explicit 'read the verifier output, not merely run it' discipline matches the skill's final proof contract.

## Prompt

```text
This backend already exists. Do not rewrite it. Inspect it and produce a staged hardening plan for the next 2 weeks.
```

## Round-2 focus verdict

FOCUS-1 (pnpm not npm): PASS — inventory row states pnpm from pnpm-lock.yaml, all verification commands and CI use pnpm with --frozen-lockfile; npm explicitly ruled out. FOCUS-2 (server baseline without a specific flaw): PASS — P1-3 adds requestTimeout/connectionTimeout/keepAliveTimeout/bodyLimit + SIGTERM/SIGINT graceful shutdown, framed as always-include, with a config/shutdown verifier.

## References loaded

- codebase-fit.md (read first, correct for retrofit)
- api-contracts.md
- auth-tenancy-security.md
- persistence-migrations.md
- reliability-async.md
- testing-verification.md
- observability-ops.md
- language-adapters.md

## Judge summary

Round 2 fully closes the round-1 regressions. Every command uses pnpm (lockfile-detected, npm explicitly contrasted) and the server baseline (timeouts + bodyLimit + graceful shutdown) appears as an always-include retrofit deliverable P1-3 even without a specific flaw. All 5 planted flaws found at correct lines; the mass-assignment P0 is actually demonstrated (privilege escalation + tenant reassignment + store corruption), and the SQL concat is ranked P0 with an honest note that the toy engine masks the exploit. Clean P0/P1/P2/P3 separation, per-stage verifiers, baseline captured before changes, no framework rewrite. Impact Read is implicit but the routing (codebase-fit first, then risk references) matches the skill's retrofit mode. Exemplary.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
Confirmed. The `PATCH /users/:id` mass-assignment is a live, demonstrated P0: sending `{role:'superadmin', orgId:'org2', id:'hacked'}` mutated the shared in-memory row so `u1` became `id:hacked, orgId:org2, role:superadmin` — privilege escalation **and** tenant reassignment in one request, and it corrupted the store (org1 can no longer see the user). The SQL string-concat in `/projects/search` did not produce a cross-tenant leak against the toy engine, so I'll rank it honestly. Here is the plan.

---

# Staged Hardening Plan — `002-ts-fastify` (TypeScript / Fastify)

**Mode:** Retrofit. Goal: preserve existing behavior and the 7 passing tests while closing production-failure surfaces, staged across 2 weeks. This is an intentionally-flawed fixture (per its own `package.json` description), so findings below are real defects, not style notes.

## Inventory (detected from lockfile + source)

| Aspect | Finding |
|---|---|
| Framework | Fastify 5.2 (ESM, `"type":"module"`) |
| Package manager | **pnpm** (`pnpm-lock.yaml`) → all commands use `pnpm` |
| Runtime | `tsx` (dev/prod both run TS directly; no build step) |
| Entrypoint | `src/server.ts` → `buildApp()` in `src/app.ts` |
| DB | `src/db.ts` — in-memory toy SQL store; `query()` returns **live row references** (documented lines 52–53) |
| Migrations | none |
| Tests | Vitest, `test/app.test.ts`, 7 happy-path tests, `pnpm test` green |
| Typecheck | `tsc --noEmit` (`pnpm typecheck`) green; `strict:true` |
| Auth | fake — trusts `x-user-id` header (stated by design); org derived server-side via `authContext` |
| Logger | **disabled** — `Fastify()` created with no `logger` option, so `req.log.*` is a no-op sink |
| CI / lint | none (no ESLint, no `no-floating-promises`, no CI workflow) |

**Baseline proof (captured before any change):** `pnpm typecheck` clean; `pnpm test` → 7 passed. Any change must keep both green.

**Assumption:** the `x-user-id` fake-auth scheme is accepted as the fixture's boundary; the plan hardens *authorization and tenant enforcement behind* that boundary, and flags real-auth as an out-of-scope follow-up rather than rewriting it.

---

## Risk map (ordered by blast radius)

### P0-1 — Mass assignment → privilege escalation + tenant reassignment + store corruption
- **Where:** `src/app.ts:36` — `Object.assign(user, req.body)` where `user` is a **live** store row (`db.ts:52–54`), plus `return { user }` (`app.ts:37`).
- **Pattern:** `api-mass-assignment` + `authz` escalation + `api-bopla-property-leak`.
- **Blast radius:** Demonstrated — `PATCH /users/u1` with `{role:'superadmin', orgId:'org2', id:'hacked'}` set `u1.role=superadmin`, moved it to `org2`, and changed its `id`; org1 then can no longer see the user. Client controls `role`, `orgId`, `id`, `email`. Cross-tenant + privilege escalation.
- **Fix shape:** allowlist writeable fields (e.g. `name` only); assign server-owned fields (`role`, `orgId`, `id`, `email`) server-side; write via explicit `UPDATE ... WHERE id=? AND orgId=?` instead of mutating the returned reference; return an explicit DTO (`{id, orgId, name, email, role}`), not the raw row.
- **Verifier:** test that `PATCH` with `{role, orgId, id}` in body leaves those fields unchanged (403 or ignored); cross-tenant patch returns 404; response contains only allowlisted fields.

### P0-2 — SQL built by string interpolation (tenant filter + user input)
- **Where:** `src/app.ts:53` — `` `SELECT * FROM projects WHERE orgId = '${ctx.orgId}' AND name LIKE '%${q}%'` ``.
- **Pattern:** `sql-string-concat`. Every other query in the file is correctly parameterized — this is the one that concatenates.
- **Blast radius:** Against the toy in-memory engine I could **not** produce a working cross-tenant leak (the regex parser + `unquote` neutralized the breakout strings I tried). But the code *shape* is textbook SQL injection and tenant-filter bypass the moment it runs against a real driver; `q` is fully user-controlled. Ranked P0 by pattern with that honest caveat — the fixture's fake DB is masking, not preventing, the exploit.
- **Fix shape:** parameterize exactly like the sibling routes — `db.query('SELECT id, orgId, name, status FROM projects WHERE orgId = ? AND name LIKE ?', [ctx.orgId, '%' + q + '%'])`; escape/validate `q` length.
- **Verifier:** search test with `q` containing `'`, `%`, and ` AND ` asserting only caller-org projects return and no error; add a Semgrep/grep gate for template-literal SQL.

### P1-1 — Unbounded, event-loop-blocking CSV export
- **Where:** `src/app.ts:72–82` — `fs.readFileSync(...)` then in-memory split/filter/join of the whole file, returned as one string.
- **Pattern:** `event-loop-blocking` + "exports are bounded work" (`api-contracts.md`).
- **Blast radius:** synchronous read blocks the event loop for all concurrent requests; no row cap / no streaming; cost grows with the table. A large `transactions.csv` stalls the whole server.
- **Fix shape:** stream with `fs.createReadStream` + line transform filtering by `ctx.orgId`, return the stream (Fastify supports stream replies); or enforce a hard row cap + async export job. At minimum switch to async `fs.promises.readFile` and cap rows.
- **Verifier:** streamed-response assertion or row-cap test; event-loop-delay check on the hot path.

### P1-2 — Floating promise on audit write
- **Where:** `src/app.ts:68` — `auditLog.record(...)` **not** awaited/void'd (contrast `app.ts:115` in `/transactions`, which awaits).
- **Pattern:** `ts-floating-promise`.
- **Blast radius:** `auditLog.record` is genuinely async (`auditLog.ts:5`); an unhandled rejection can crash the process under Node's default `unhandledRejection` behavior, and the audit event for `project.created` is fire-and-forget with no error handling.
- **Fix shape:** `await auditLog.record(...)` inside a try/catch (mirror the transactions route), or explicitly `void` with a `.catch` that logs.
- **Verifier:** enable `@typescript-eslint/no-floating-promises` and run lint; the rule flags line 68.

### P1-3 — Server baseline missing (always-include)
- **Where:** `src/app.ts:20` (`Fastify()` with no options) and `src/server.ts` (no shutdown handling).
- **Pattern:** slow-client / resource-exhaustion; no graceful drain.
- **Blast radius:** no `requestTimeout`, `connectionTimeout`, `keepAliveTimeout`, or explicit `bodyLimit`; a slow or stalled client can hold connections open. No `SIGTERM`/`SIGINT` handler → in-flight requests dropped on deploy. Logger disabled means the one `req.log.error` (`app.ts:117`) writes nowhere.
- **Fix shape:** `Fastify({ logger: true, requestTimeout: 30_000, connectionTimeout: 10_000, keepAliveTimeout: 5_000, bodyLimit: 1_048_576, requestIdHeader: 'x-request-id' })`; add `process.on('SIGTERM'|'SIGINT', () => app.close())` in `server.ts` with a drain timeout.
- **Verifier:** startup config test asserting the options are set; a graceful-shutdown test that `app.close()` resolves; confirm a correlation id appears in log output.

### P1-4 — Full rows / `SELECT *` returned on public paths
- **Where:** `src/app.ts:44` (`return { project: rows[0] }` from `SELECT *`), `app.ts:33/37` (PATCH returns full user row), `app.ts:26` `/users` is the only route with an explicit projection.
- **Pattern:** `select-star-public-response` + `api-bopla-property-leak`.
- **Blast radius:** any column added to the store later (secrets, internal flags) auto-leaks into responses; user rows carry `email`.
- **Fix shape:** explicit column projections in the query + explicit response DTOs; assert forbidden fields absent in tests.
- **Verifier:** response-shape test asserting exact key set per endpoint.

### P2-1 — No pagination on growable collections
- **Where:** `/users` (`app.ts:23`), `/projects/search` (`app.ts:49`) return unbounded arrays.
- **Pattern:** `api-pagination-late` — adding it later breaks array-expecting consumers.
- **Fix shape:** add `limit`/`cursor` with a max cap and stable ordering now, while there are no external consumers.
- **Verifier:** max-page-size + stable-order tests.

### P2-2 — Mutating POSTs are not idempotent (money path)
- **Where:** `/projects` (`app.ts:57–70`), `/transactions` (`app.ts:98–122`); ids via `Math.random` (`app.ts:61,106`).
- **Pattern:** `api-idempotency-missing-on-mutation-retry`. Transactions move money-shaped data.
- **Fix shape:** accept an `Idempotency-Key` header; persist key+fingerprint→result; replay on duplicate. Note the outbox/transaction-boundary requirement for the DB-write-then-audit-write pair even though the current store has no transactions.
- **Verifier:** duplicate-request test asserting one row created.

### P2-3 — No input schema on `POST /projects`; unsafe `as any`
- **Where:** `src/app.ts:60` (`req.body as any`, `body.name` unchecked) — contrast `/transactions` which has a JSON schema.
- **Pattern:** boundary validation gap; can insert a project with `undefined`/`null` name.
- **Fix shape:** add a Fastify JSON schema (`required:['name']`, `additionalProperties:false`) mirroring the transactions route.
- **Verifier:** validation-error (400) test for missing/extra fields.

### P2-4 — Security events not tagged; no correlation id in errors
- **Where:** 401 branches (`app.ts:25,32,43,51,59,74,103`) return generic JSON, log nothing; no shared error contract.
- **Pattern:** `observability-no-correlation-id`, `api-error-contract-drift`.
- **Fix shape:** shared error handler (`setErrorHandler`) emitting stable codes + request id; emit an explicitly-tagged security event on auth failures.
- **Verifier:** contract test over representative 400/401/404/500; assert request id present.

### P3 — `Math.random` ids
- Low collision risk; migrate to `crypto.randomUUID()` when touching those routes (folds into P2-2).

---

## Two-week staged plan

Each stage ends green on `pnpm typecheck` && `pnpm test`, and adds the failing-path test that proves the fix before/with the change. No stage alters an existing passing test's expectation except where the contract is intentionally tightened (documented in that stage).

### Week 1 — Stop the bleeding (P0/P1), plus the tooling that keeps them fixed

**Stage 0 (Day 1) — Tooling gate.** Add ESLint + `typescript-eslint` with `no-floating-promises` and `no-explicit-any` (type-checked lint), and a `pnpm lint` script; add a Semgrep/grep rule for template-literal SQL. Add a minimal CI workflow running `pnpm install --frozen-lockfile && pnpm lint && pnpm typecheck && pnpm test`. *No behavior change.* This makes P1-2, P0-2, and P2-3 mechanically catchable. Verifier: `pnpm lint` flags `app.ts:68` and `app.ts:53/60`.

**Stage 1 (Day 1–2) — P0-1 mass assignment.** Allowlist writeable fields on `PATCH /users/:id`, write via explicit `UPDATE`, return a DTO. Add tests: forbidden-field patch is ignored/rejected, cross-tenant patch → 404, response key-set locked. This is the highest-blast-radius, already-demonstrated defect — do it first.

**Stage 2 (Day 2–3) — P0-2 SQL string-concat.** Parameterize `/projects/search`; validate/bound `q`. Add injection/cross-tenant search test. Confirm the Semgrep rule from Stage 0 now passes.

**Stage 3 (Day 3–4) — P1-3 server baseline.** Add Fastify timeouts + `bodyLimit` + `logger:true` + request id; add `SIGTERM`/`SIGINT` graceful shutdown in `server.ts`. Config + shutdown tests. This also makes the existing `req.log.error` actually record.

**Stage 4 (Day 4) — P1-2 floating promise.** Await `auditLog.record` in `/projects` inside try/catch (mirror `/transactions`). Lint rule from Stage 0 confirms zero floating promises.

**Stage 5 (Day 5) — P1-1 export.** Stream the CSV export (or hard row-cap + async read); keep the org-filter behavior identical so the existing export test stays green. Add streamed-response / row-cap assertion.

### Week 2 — Contract and durability hardening (P1-4 → P2), each behind a test

**Stage 6 (Day 6–7) — P1-4 DTOs + explicit projections.** Replace `SELECT *`/raw-row returns on `/projects/:id`, PATCH, and search with explicit column lists and response DTOs. Add forbidden-field-absent tests. Document any intentional response-shape tightening.

**Stage 7 (Day 7–8) — P2-3 input schema on `POST /projects`.** Add JSON schema, drop `as any`. Validation-error tests.

**Stage 8 (Day 8–10) — P2-2 idempotency (money path first).** Add `Idempotency-Key` handling to `/transactions`, then `/projects`; switch ids to `crypto.randomUUID()` (absorbs P3). State the DB-write + audit-write transaction/outbox boundary even though the toy store has no transactions. Duplicate-request test asserting one side effect.

**Stage 9 (Day 10–11) — P2-1 pagination.** Add `limit`/`cursor` (capped) with stable ordering to `/users` and `/projects/search`. Because there are no external consumers yet, this is the cheapest it will ever be. Max-page-size + ordering tests.

**Stage 10 (Day 12) — P2-4 error contract + security events.** Central `setErrorHandler` with stable codes + request id; tag auth-failure security events. Contract test over 400/401/404/500.

**Stage 11 (Day 13–14) — Regression + real-dependency note.** Full `pnpm lint && pnpm typecheck && pnpm test` sweep; add negative/boundary tests for any surface still happy-path-only. Document residual risk: the in-memory `db.ts` does not model real locks/transactions/constraints — persistence-semantics tests (`testing-verification.md`) will need a real engine (e.g. Testcontainers) before this is production-representative, and the `x-user-id` fake auth must be replaced with real authentication as a separate track.

---

## Verification commands (project-local, pnpm)

```
pnpm install --frozen-lockfile
pnpm lint         # added Stage 0: no-floating-promises, no-explicit-any, sql-concat rule
pnpm typecheck    # tsc --noEmit
pnpm test         # vitest run
```

Every stage's proof = the new failing-path test named above going green **without** regressing the original 7. Approve a stage only when its verifier output has been read, not merely run.

---

## Files read
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (skill body, provided inline)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/package.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/tsconfig.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/vitest.config.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/src/app.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/src/server.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/src/db.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/src/auditLog.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/test/app.test.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/002-ts-fastify/data/transactions.csv
````
