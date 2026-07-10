# forward-test 008: node-csv-export

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 3/4
Generic advice: False
Verifier quality (judge): Strong: pnpm test (17/17, output inspected) and tsc --noEmit both cited and independently reproduced by grader; new tests directly assert the changed behavior (401, stable header + attachment headers, DB-backed export of an API-created row, bidirectional tenant isolation) plus 6 encoder unit tests. Weakness: no verifier for the non-blocking/bounded-memory claim (no event-loop delay check or size-cap test), matching the two missed behaviors.

## Prompt

```text
Add CSV export for all transactions from an HTTP endpoint in our TypeScript API.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/api-contracts.md
- references/auth-tenancy-security.md
- references/language-adapters.md
- references/testing-verification.md
- references/codebase-fit.md
- references/library-decisions.md

## Judge summary

Verified answer against repo: all claims true, 17/17 tests and typecheck independently reproduced. Strong run — found the planted event-loop-blocking flaw plus non-obvious extras (comma-split tenant misrouting, formula injection, live-row mutation), correct tenant scoping with bidirectional isolation tests, correct reference routing, concrete behavior-specific verifiers. Held at 3 because two expected behaviors were argued around rather than implemented: the CSV body is still fully materialized in memory (no streaming/async job) and there is no cap on export size; also skipped reliability-async.md, though that traces to a routing-table signal gap.

## Misses

- does not stream or use an async export job: toCsv (src/csv.ts:19-26) still materializes the whole CSV string in memory; the agent justified it via the bounded in-memory store and left a comment, but the expected behavior is absent from the implementation
- no cap on export input/output: no row limit, cursor, or pagination on an endpoint over an unbounded-growth collection; a cap is never even discussed
- did not load references/reliability-async.md, which contains the event-loop-blocking failure card and bounded-work guidance (mitigated: the routing table has no signal word that maps 'export/streaming/bulk' to that file)

## Changes needed in skill/reference/failure card

- Add 'export, CSV/bulk download, report generation, streaming response, large payload, event loop' to the reliability-async.md signal row (and cross-link from language-adapters.md's Event loop section) in the SKILL.md routing table so bulk-export tasks load the event-loop-blocking card
- Add an 'unbounded-export' rule to api-contracts.md (next to 'Pagination is a launch decision') or a failure card: any full-collection export must bound work — hard row cap, cursor pagination, streamed response, or async job with download link — and 'the dataset is small today' is explicitly not an accepted waiver
- In the event-loop-blocking failure card / language-adapters event-loop verifier, require a concrete proof for the non-blocking claim (row-cap test or streamed-response assertion), since the tested agent's otherwise strong test matrix had no verifier for memory/blocking behavior

## Tested agent answer (verbatim)

````text
All green — 17/17 tests pass, typecheck clean. The work is complete.

## What changed

**Finding first:** the fixture already had `GET /transactions/export`, but it was broken in four ways: it read a stale static file (`data/transactions.csv`) instead of the store the API writes to — so transactions created via `POST /transactions` never appeared in "all transactions"; it used `fs.readFileSync` in the request handler (event-loop blocking); it filtered tenants by naive `line.split(',')[1]` (a comma inside any field misroutes rows across the tenant boundary); and it emitted unescaped values (malformed CSV + spreadsheet formula injection surface).

**Changes (scoped to the export surface, per the skill's "smallest boundary that owns the behavior" rule):**

1. `/Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/csv.ts` (new) — RFC 4180 encoder: quotes fields containing `,` `"` CR/LF, doubles embedded quotes, neutralizes spreadsheet formula triggers (`=` `+` `-` `@` tab/CR prefixes) in string cells with a leading `'`, passes finite numbers through untouched so negative amounts are never mangled. `toCsv(columns, rows)` renders header + rows with CRLF endings. No dependency added — per the skill's library-decisions gate, this surface is too small to justify one, and the encoder is unit-tested.

2. `/Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts` — the export handler now:
   - queries the in-memory DB (source of truth) with the existing parameterized pattern: `SELECT ... FROM transactions WHERE orgId = ?` with the **server-derived** `ctx.orgId` (tenant id never comes from the client);
   - maps rows through an explicit column allowlist `['id','orgId','projectId','amount','currency']` — this is the DTO, important because `db.query()` returns whole live rows regardless of the SELECT list (also means no accidental mutation of live rows: read-only mapping);
   - sets `content-type: text/csv; charset=utf-8`, `content-disposition: attachment; filename="transactions.csv"` (static filename, no header-injection surface), and `cache-control: no-store` (financial data);
   - no sync filesystem I/O anywhere; removed the dead `fs`/`fileURLToPath`/`DATA_DIR` imports.

3. Tests (proof matrix: public endpoint → success + auth + contract; tenant-owned data → cross-tenant denial):
   - `/Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/app.test.ts` — 4 new cases: 401 without auth; stable header row + attachment header; export contains a transaction created through the API (exact row `"{id},org1,p2,77,EUR"` — proves DB-backed export); bidirectional tenant isolation (`org2` export contains no `org1` substring and vice versa). The pre-existing export test passes unchanged (behavior-preservation proof for the old assertions).
   - `/Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/csv.test.ts` — 6 unit cases: passthrough, quoting/escaping/newlines, formula-trigger neutralization, negative numbers untouched, null/undefined as empty, CRLF framing and empty-rows case.

## Proof (final proof contract)

- `pnpm test` → **2 files, 17 tests passed** (11 in app.test.ts including the 4 new export tests, 6 in csv.test.ts), output inspected above.
- `pnpm typecheck` (`tsc --noEmit`, strict) → clean, no output.

## Assumptions and residual notes

- **Assumption:** the in-memory DB store is the source of truth for transactions (it's the write path of `POST /transactions`); `data/transactions.csv` was a stale snapshot and is now unused by the app. I left the file in place rather than deleting fixture data.
- **Streaming/pagination:** the store is in-memory and bounded, so building the body in memory is fine; with a real driver this endpoint should stream rows from a cursor (`reply.send(Readable)`) rather than paginate — noted in a handler comment.
- **Line endings changed** from `\n` to RFC 4180 CRLF; no consumer contract asserted `\n` (existing test uses substring checks and still passes).
- **Out of scope, observed but not fixed** (pre-existing planted flaws in other routes, would bloat this change): mass assignment in `PATCH /users/:id` (app.ts:36), SQL string concatenation in `/projects/search` (app.ts:53 pre-edit numbering), unvalidated `as any` body + un-awaited `auditLog.record` in `POST /projects`.

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/codebase-fit.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/db.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/server.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/auditLog.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/package.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/tsconfig.json
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/test/app.test.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/data/transactions.csv
````
