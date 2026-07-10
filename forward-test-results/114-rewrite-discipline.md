# forward-test 114: rewrite-discipline (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 3/4 (round 1: 4/4)
Round-1 miss closed: False
Generic advice: False
Verifier quality (judge): Strong: pnpm typecheck clean and 13/13 vitest pass, independently reproduced by grader in the working copy; 6 new boundary tests encode the actual invariants (mass-assign has no effect, quote-bearing search neither crashes nor leaks org2 data, partial-name search still works, missing-name rejected, client-supplied orgId ignored); the mass-assignment exploit was demonstrated live before fixing; Fastify server-option names verified against the installed 5.10.0 rather than guessed.

## Prompt

```text

```

## Round-2 focus verdict

Focus 1 (server baseline in hardening plan): PASS — bodyLimit/requestTimeout/connectionTimeout listed as finding #6, implemented at src/app.ts:22-26, option names verified against Fastify 5.10.0. Focus 2 (routing): PARTIAL FAIL — reliability-async.md IS in Files read for the floating-promise finding (PASS half), but testing-verification.md is NOT in Files read despite the agent writing test/hardening.test.ts with 6 new tests, which SKILL.md Retrofit mode explicitly gates on loading that reference (FAIL half).

## References loaded

- SKILL.md
- references/library-decisions.md
- references/codebase-fit.md
- references/auth-tenancy-security.md
- references/reliability-async.md

## Judge summary

Excellent substantive answer: refuses the NestJS/persistence rewrite as framework-rewrite-as-cleanup, finds all 5 planted flaws plus the non-planted db.ts live-reference footgun, fixes them in place with contracts preserved, and the proof independently reproduces (tsc clean, 13/13 vitest). Round-2 focus item 1 (server baseline timeouts + bodyLimit) is fully closed and verified against the installed Fastify version. Round-2 focus item 2 is only half closed: reliability-async.md was loaded, but testing-verification.md is absent from Files read even though the agent wrote a new 6-test regression file — the exact trigger the round-1 fix added to Retrofit mode. Score capped at 3 for the open routing regression.

## Misses

- ROUND-2 FOCUS: testing-verification.md NOT in Files read despite the agent prescribing and writing a new 6-test regression file (test/hardening.test.ts) — SKILL.md Retrofit mode explicitly requires loading it before writing the verifier plan, and the routing row 'tests, CI' matched
- Secondary routing gap: persistence-migrations.md not loaded despite the SQL signal row matching (SQL injection fix, persistence-rewrite question)
- Minor: comment at src/app.ts:38 claims additionalProperties:false 'rejects (400)' while AJV removeAdditional actually strips extra fields (the test file and answer prose describe stripping correctly, so behavior claims are accurate)

## Changes needed

- SKILL.md routing table: strengthen the testing row signal from 'tests, CI, contract testing, DB integration tests' to explicitly include 'adding or writing any new test file, regression tests for a fix' so writing tests (not just planning CI) unambiguously triggers references/testing-verification.md
- SKILL.md Final proof contract: add a line 'If the change adds or modifies tests, references/testing-verification.md must appear in the Files read list' — makes the round-1 fix self-enforcing at report time rather than relying on the Retrofit-mode sentence being remembered mid-task
- SKILL.md routing table SQL row: add 'fixing SQL injection / parameterizing queries' as an explicit signal for references/persistence-migrations.md, since agents treat an injection fix as security-only and load auth-tenancy-security.md but skip the persistence reference

## Tested agent answer (verbatim)

````text
## Recommendation: No — do not move it to NestJS, and do not "rewrite the persistence layer" as a cleanup. Fix the actual defects in place.

This is a textbook `framework-rewrite-as-cleanup` (backend-craft `library-decisions.md`). "Messy" here is a short list of concrete, localized bugs — none of which a framework change fixes, and a big-bang rewrite would (a) discard the only tests that currently prove your tenant boundaries and (b) re-introduce the same bugs in unfamiliar new code. I proved the point by fixing every real issue in place in one small pass: the whole route file is 182 lines, all 7 original contract tests still pass, and I added 6 boundary regression tests. Total change touched one file plus one new test file.

### What "messy" actually is (findings, original line numbers)

| # | Sev | File:line | Defect | Blast radius |
|---|-----|-----------|--------|--------------|
| 1 | **P0** | `src/app.ts:36` | `Object.assign(user, req.body)` — unvalidated mass-assign into a live store row (`api-mass-assignment`) | Privilege escalation + tenant move. **Proven exploitable**: `PATCH /users/u1 {role:"admin", orgId:"org2", id:"HACKED"}` returned 200 and rewrote all three server-owned fields. |
| 2 | **P0-pattern** | `src/app.ts:53` | `SELECT ... WHERE orgId = '${ctx.orgId}' AND name LIKE '%${q}%'` — string interpolation of user input + tenant id into SQL | Classic injection / `tenant-filter` bypass. The toy in-memory store lacks `OR` semantics so it isn't *widenable in this fixture*, but this becomes a cross-tenant P0 the instant it points at a real database — i.e. exactly the "rewrite persistence" scenario being proposed. Every other route already parameterizes; only this one broke discipline. |
| 3 | P2 | `src/app.ts:68` | `auditLog.record(...)` not awaited (`ts-floating-promise`) | Lost/racy audit writes, unhandled rejection. Note the `/transactions` route at :115 awaits the same call correctly — the codebase already knows the right pattern. |
| 4 | P2 | `src/app.ts:57` | `POST /projects` has no body schema; `body.name` can be undefined/any | Junk rows, `name` inserted as `undefined`. |
| 5 | P2 | `src/app.ts:75` | `fs.readFileSync` on the export hot path (`event-loop-blocking`) + whole-file read | Blocks the event loop; unbounded memory as the CSV grows. |
| 6 | P2 | `buildApp` | No `requestTimeout` / `connectionTimeout` / `bodyLimit` (retrofit server baseline) | Slow-client / oversized-body resource exhaustion. |
| 7 | P2 | `src/db.ts:54` | `query()` returns **live** row references; the file even warns "read handlers must not mutate what they read" | This is the footgun finding #1 rode on — a mutation on a "read" result writes straight to the store. |

### Why NestJS + a persistence rewrite is the wrong tool

- **The mess is not framework-caused.** Fastify already gives you JSON-schema validation, and the codebase uses it correctly on `/transactions`. The bugs are missing-validation, string-interpolation, and a floating promise. NestJS ships none of those fixes for free — you'd re-hand-write the same handlers and can reproduce every bug.
- **A rewrite maximizes blast radius.** It puts all 7 API contracts, the tenant-scoping logic, and your only test suite in flight simultaneously — the highest-risk possible path — and it launders the existing P0s into new code where your current tests no longer guard them.
- **"Rewrite the persistence layer" is conflating two things.** Today's `db.ts` is a fake in-memory SQL parser (a fixture). Wanting a *real* database (Postgres + a typed query builder / migrations — Kysely or Drizzle per `library-decisions.md`) is legitimate, but that's driven by needing durability/queries, **not** by "the service is messy," and it's orthogonal to the HTTP framework. Do it as its own staged workstream behind the unchanged route contracts and tests — never bundled into a framework swap.

The skill's own escape hatch is explicit: *"Do not migrate an existing Express app to Fastify/NestJS during a feature fix unless the task is explicitly a framework migration."* The right move is Retrofit mode: preserve behavior, harden by blast radius.

### What I changed (in place, contracts preserved)

`src/app.ts` — the only source file touched:
- **#1 fixed:** `PATCH /users/:id` now has a body schema allowlisting only `name`/`email`; Fastify's AJV strips server-owned `role`/`orgId`/`id` before the handler, and the handler applies only allowlisted fields. Escalation no longer takes effect.
- **#2 fixed:** `/projects/search` is now parameterized (`WHERE orgId = ? AND name LIKE ?`, values `[ctx.orgId, \`%${q}%\`]`) with a querystring schema capping `q` length. Search results unchanged.
- **#3 fixed:** `POST /projects` now `await`s `auditLog.record(...)`.
- **#4 fixed:** `POST /projects` got a required-`name` body schema (mirrors `/transactions`).
- **#5 fixed:** export switched to async `fs.promises.readFile` (un-blocks the event loop; behavior identical).
- **#6 fixed:** `Fastify({ bodyLimit: 256 KiB, requestTimeout: 30_000, connectionTimeout: 10_000 })` — verified these option names against installed Fastify 5.10.0.

`test/hardening.test.ts` (new) — 6 regressions encoding the boundaries: mass-assign does not take effect, quote-bearing search neither crashes nor leaks `org2`'s project, partial-name search still works, `POST /projects` rejects missing name, and a client-supplied `orgId` is ignored in favor of the server-derived tenant.

### Proof

- `pnpm typecheck` (`tsc --noEmit`): clean.
- `pnpm test` (vitest): **13 passed (13)** — all 7 original contract tests in `test/app.test.ts` still green (behavior preserved) plus the 6 new boundary tests.
- Package manager: `pnpm` (detected from `pnpm-lock.yaml`).

### Follow-ups I intentionally did not bundle in (separate, staged)

- **#7 / real DB:** if you do want durability, replace the fake `db.ts` with Postgres + Kysely or Drizzle behind the unchanged repository calls and tests — a scoped workstream, not part of any framework decision. This also retires the live-reference footgun.
- **Export streaming:** the async read un-blocks the loop but still buffers the file; when the dataset grows, stream it (`createReadStream` + line filter) with a row cap.
- **IDs:** `Math.random()` ids (`src/app.ts` in `POST /projects` and `/transactions`) should move to `crypto.randomUUID()`; low risk, left as-is since it's fixture data.

If the team's real goal is enterprise structure/DI conventions, that's a values choice you can adopt incrementally inside Fastify (plugins, decorators) without a rewrite — and it should be decided on team-ergonomics grounds, after these P0s are closed, not as a bug-fix strategy.

### Files read
- `/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md`
- `/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md`
- `/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md`
- `/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md`
- `/Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/package.json`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/tsconfig.json`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/vitest.config.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/src/app.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/src/db.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/src/auditLog.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/src/server.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/test/app.test.ts`
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/014-ts-fastify/data/transactions.csv`
````
