# forward-test 108: node-csv-export (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify
Ground truth: /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify
Score: 4/4 (round 1: 3/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong: row-cap test (seeds 10,001 rows in an isolated org, asserts 413 + exact error body against the exported cap constant), freshness test proving DB-sourced export, per-row tenant assertion, exact download-header assertions, 8 CSV encoder unit tests. Grader re-ran typecheck and tests: clean, 19/19 pass.

## Prompt

```text

```

## Round-2 focus verdict

Focus 1 (stream/job, not unbounded in-memory): SATISFIED via the skill-sanctioned hard-row-cap variant — build is bounded at 10k rows with 413 beyond and documented async-job growth path (focus item 2 explicitly accepts a hard cap). Focus 2 (hard cap, no small-dataset waiver): SATISFIED. Focus 3 (concrete verifier): SATISFIED — row-cap 413 test, independently reproduced. reliability-async.md present in Files read as required.

## References loaded

- SKILL.md
- references/reliability-async.md
- references/api-contracts.md
- references/auth-tenancy-security.md

## Judge summary

Round-2 fixes worked. The agent loaded reliability-async.md via the new routing-table row, applied the 'Exports are bounded work' rule (hard 10k row cap + 413, async-job growth path documented, no small-dataset waiver), and shipped the prescribed verifier: a 10,001-row seeded row-cap test asserting 413, plus a freshness test that kills the round-1 stale-file flaw. It also fixed the comma-split tenant filter (cross-tenant leak), kept tenant scoping parameterized and server-derived, added RFC 4180 escaping and formula-injection defense, and its proof (tsc clean, 19/19 vitest) reproduced exactly when re-run. Only residual: the cap is applied after fetching all rows rather than in the query — harmless with the fake DB, worth a one-line reference tightening.

## Misses

- Minor: cap is checked after fetching all org rows; against a real DB the query itself is still unbounded work (should be LIMIT cap+1). Acceptable here given the in-memory fake DB has no LIMIT, but the residual was not called out.

## Changes needed

- Optional tightening: in api-contracts.md 'Exports are bounded work' (or reliability-async.md verifiers), add that a hard row cap must be enforced in the query itself (e.g. LIMIT cap+1) rather than after materializing all rows, so the DB read is bounded too.

## Tested agent answer (verbatim)

````text
CSV export for all transactions implemented at `GET /transactions/export` in the Fastify fixture, following backend-craft (Continue mode, Impact Read → api-contracts + auth-tenancy + reliability-async references).

## What existed and what was wrong

The route already existed but was flawed (this fixture is intentionally flawed; the task is scoped to the export, so other deliberate flaws — SQL injection in `/projects/search`, mass assignment in `PATCH /users/:id` — were left untouched):

1. **Stale data source** — it read `data/transactions.csv` from disk, not the `transactions` table. Transactions created via `POST /transactions` never appeared in the export; the file even contained a row (`t4`) that does not exist in the DB.
2. **Fragile tenant filter** — org scoping was `line.split(',')[1] === ctx.orgId`. Any field containing a comma shifts columns, silently dropping rows or cross-tenant-leaking them (P0 pattern `tenant-filter-forgotten` by construction).
3. **No CSV escaping, no download headers, unbounded work, no audit event.**

## Implementation (assumption stated)

Assumption: the DB is the system of record; the file was a stale snapshot, so `t4` (file-only) intentionally disappears from exports. `data/transactions.csv` is left in place as fixture data but is no longer read by the app.

- `src/csv.ts` (new): dependency-free RFC 4180 encoder — quotes fields containing `, " \r \n`, doubles embedded quotes, and neutralizes spreadsheet formula-injection prefixes (`= + - @ \t \r`) in text cells only (numbers, incl. negatives, pass through).
- `src/app.ts` (modified):
  - Query is tenant-scoped server-side (`WHERE orgId = ?`, parameterized, explicit column list), tenant id derived from auth, never from the client.
  - Explicit DTO allowlist `TRANSACTION_EXPORT_COLUMNS = ['id','orgId','projectId','amount','currency']` — persistence-row fields never leak by accident even though the fake DB returns full rows.
  - **Bounded work** (skill non-negotiable "Exports are bounded work"): exported `TRANSACTION_EXPORT_MAX_ROWS = 10_000`; beyond it the endpoint returns `413 {error, maxRows}` instead of buffering unbounded payloads. Growth path documented in-code: async export job + download link.
  - Deterministic ordering (sort by id on a copy — `db.query` returns live store references, so no mutation of the store).
  - Headers: `text/csv; charset=utf-8`, `content-disposition: attachment; filename="transactions.csv"`, `cache-control: no-store` (financial data). CRLF line endings per RFC 4180.
  - Awaited `auditLog.record('transactions.exported', {orgId, userId, rowCount})` — no floating promise, no PII beyond ids/counts.
  - Removed now-unused `fs`/`fileURLToPath` imports.
- `test/csv.test.ts` (new): 8 unit tests for quoting, escaping, formula-prefix neutralization.
- `test/app.test.ts` (modified): kept the existing org-scoping test unchanged; added 4 tests — export 401, exact headers + header row + every data row in caller org with 5 columns, freshness (a transaction created via POST appears in the next export: kills the stale-file flaw), and the row-cap test seeding a dedicated org with 10_001 rows and asserting 413 (the reliability-async verifier: concrete proof of bounded work, not a "dataset is small" comment).

## Proof (final proof contract)

- `pnpm typecheck` (tsc --noEmit): clean, no output.
- `pnpm test` (vitest): **2 files, 19/19 tests passed** — including `exports transactions for the caller org only` (pre-existing contract preserved), `exports transactions from the database, including ones created after startup`, and `refuses exports beyond the row cap (bounded work)`.

## Files changed

- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/app.ts` (modified)
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/csv.ts` (new)
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/test/csv.test.ts` (new)
- `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/test/app.test.ts` (modified)

## Files read

- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/app.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/db.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/server.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/src/auditLog.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/test/app.test.ts
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/package.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/tsconfig.json
- /private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/round2/008-ts-fastify/data/transactions.csv
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (skill body, loaded via Skill tool)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
````
