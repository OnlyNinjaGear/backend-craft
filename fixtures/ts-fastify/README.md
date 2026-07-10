# ts-fastify — intentionally flawed backend fixture

## Purpose

This is a small, runnable multi-tenant SaaS API (users, projects, transactions)
built with **TypeScript + Fastify + vitest**. It exists to **forward-test the
`backend-craft` code-review skill** and to **exercise the Semgrep rule pack** in
`rules/semgrep/backend-craft.yml`.

It contains **exactly 5 planted production-safety flaws**, each mapped to a
failure card in `FAILURE_CARDS.md` and marked in code with a single comment:

```ts
// PLANTED: <card-id>
```

Nothing else about each flaw is called out in code. The flaws are **not compile
errors** — `tsc --noEmit` (strict) passes and the happy-path tests pass. They are
production-safety defects that look plausible and survive a green build.

The fixture also includes **clean contrast code** (parameterized SQL, an awaited
async call, explicit error handling, a JSON-schema-validated route) so checker
false positives can be measured against true positives.

Fake auth: every request carries an `x-user-id` header; the server derives the
caller's `orgId` (tenant) from that user, never from the request body.

## How to run the tests

```bash
cd /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify && pnpm install && pnpm test
```

`pnpm install` allows esbuild's build script automatically (see
`pnpm.onlyBuiltDependencies` in `package.json`), so no `pnpm approve-builds` step
is needed. All 7 tests should pass.

Extra commands:

- `pnpm typecheck` — `tsc --noEmit` with `strict: true` (passes; `as any` is legal under strict).
- `pnpm start` — run the server on `PORT` (default 3000) via `tsx`.

## Expected failures

Exactly 5 planted flaws. All live in `src/app.ts`.

| card id | file:line area | one-line description |
| --- | --- | --- |
| `api-mass-assignment` | `src/app.ts:36` (PATCH `/users/:id`) | `Object.assign(user, req.body)` lets a client set server-owned fields like `role`/`orgId`. |
| `sql-string-concat` | `src/app.ts:53` (GET `/projects/search`) | Search builds SQL via template-literal interpolation of the `q` query param — SQL injection. |
| `ts-any-at-boundary` | `src/app.ts:60` (POST `/projects`) | `const body = req.body as any`; fields trusted with no runtime validation and no Fastify schema. |
| `ts-floating-promise` | `src/app.ts:68` (POST `/projects`) | `auditLog.record(...)` (async) is called as a bare statement — no `await`/`void`/`catch`. |
| `event-loop-blocking` | `src/app.ts:75` (GET `/transactions/export`) | `fs.readFileSync` in the handler + the whole CSV built in memory before responding — blocks the event loop. |

## Clean contrast code (should NOT be flagged)

| location | clean pattern |
| --- | --- |
| `src/app.ts` `authContext` / GET `/users` / GET `/projects/:id` | Parameterized `db.query(sql, params)` with tenant scoping. |
| POST `/transactions` (`src/app.ts`) | Proper Fastify JSON schema (`required`, `enum`, `additionalProperties:false`). |
| POST `/transactions` (`src/app.ts`) | `await auditLog.record(...)` — properly awaited async call. |
| POST `/transactions` (`src/app.ts`) | `try/catch` with explicit error response and no payload/secret leak. |

Note: the Semgrep floating-promise rule was **retired** (2026-07-10) exactly
because of the noise this fixture measured — Semgrep matches subexpressions, so
awaited/assigned `db.query(...)` and `reply.send(...)` calls fired too
(precision ~1/8; see `../../CHECKERS.md`). The `ts-floating-promise` plant at
`src/app.ts:68` is therefore **not Semgrep-detectable by design**; its verifier
is type-aware `@typescript-eslint/no-floating-promises`. Expected Semgrep hits
for this fixture: exactly 3 (`mass-assignment-request-body`,
`sql-template-query`, `sync-fs-in-code`).

## Files

```
ts-fastify/
├── package.json          # deps: fastify; dev: vitest, typescript, tsx, @types/node
├── tsconfig.json         # strict: true, moduleResolution: Bundler
├── vitest.config.ts
├── data/transactions.csv # read by the export handler
├── src/
│   ├── db.ts             # in-memory pretend-SQL: query(sql, params?), execute(sql, params?) — CLEAN infra
│   ├── auditLog.ts       # async audit sink used to demo floating vs awaited promise
│   ├── app.ts            # all routes; all 5 planted flaws are here
│   └── server.ts         # entrypoint (pnpm start)
└── test/app.test.ts      # 7 happy-path tests via fastify.inject
```
