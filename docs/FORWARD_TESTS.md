# backend-craft forward tests

Forward tests validate whether the skill changes agent behavior on realistic
tasks. Run these in fresh threads. Do not leak expected findings or diagnoses to
the tested agent.

Prompt shape:

```text
Use the backend-craft skill at /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft to complete this task:

<task>
```

Isolation rules (learned 2026-07-10 the hard way):

- Tested agents MUST work on a disposable copy of the fixture, or be told the
  task is design/review-only with no file edits. Implementation-shaped prompts
  ("add an endpoint...") make agents edit the fixture in place, which destroys
  planted flaws and contaminates concurrently running tests.
- Tell the tested agent not to read grading materials: repo-root
  `../FAILURE_CARDS.md`, `FORWARD_TESTS.md`, `CHECKERS.md`, `EVIDENCE_LOG.md`,
  `SOURCES.md`, `../forward-test-results/`, `../rules/`, and the fixture `README.md`.
- After any forward-test run, restore fixtures from a pristine snapshot and
  re-run the fixture test suites plus the Semgrep acceptance pass
  (`CHECKERS.md`) before trusting them again.

Evaluate:

- Did the agent perform an Impact Read?
- Did it load the right reference files?
- Did it avoid generic advice?
- Did it cite concrete files/commands/tests when available?
- Did it identify blast radius before language details?
- Did final proof match the changed behavior?

## Synthetic tasks

### 1. Start mode: small SaaS API

Ask:

```text
Design the backend foundation for a small B2B SaaS: users, organizations, projects, invoices, and webhooks. Use Python unless there is a strong reason not to. I want something maintainable for a team of 2.
```

Expected behavior:

- chooses stack with tradeoffs
- defines tenant model early
- includes API contract, migrations, auth, idempotent webhooks, tests, observability
- avoids overbuilding microservices

### 2. Retrofit mode: existing repo inventory

Ask on a real or fixture repo:

```text
This backend already exists. Do not rewrite it. Inspect it and produce a staged hardening plan for the next 2 weeks.
```

Expected behavior:

- inventories framework, package manager, DB, migrations, tests, CI
- separates P0/P1 safety issues from style debt
- uses project-local commands

### 3. API endpoint with tenant ownership

Fixture: route `GET /projects/:id` fetches by id only.

Ask:

```text
Add an endpoint to fetch a project by id for the current user.
```

Expected behavior:

- catches tenant/object authorization
- queries by id plus tenant/org scope or policy
- adds forbidden cross-tenant test

### 4. Mutating payment/order endpoint

Ask:

```text
Add an endpoint that creates an order and calls a payment provider. Clients may retry on network failures.
```

Expected behavior:

- requires idempotency key
- avoids transaction around network call
- suggests outbox/state machine when appropriate
- tests duplicate request

### 5. Unsafe migration

Fixture: large `orders` table.

Ask:

```text
Add a non-null column with a default to orders and backfill old rows.
```

Expected behavior:

- flags hot-table DDL/backfill risk
- proposes expand/contract, batched backfill, lock analysis
- requires dry run or maintenance-window note

### 6. Queue consumer

Ask:

```text
Implement a worker that consumes invoice events and emails customers.
```

Expected behavior:

- assumes duplicate delivery
- adds idempotency/dedupe
- handles poison messages and shutdown
- tests duplicate event

### 7. Retry wrapper

Ask:

```text
Our external CRM API sometimes times out. Add retries around the call.
```

Expected behavior:

- asks whether operation is idempotent/mutating
- bounded exponential backoff with jitter
- respects Retry-After
- no retry on permanent errors

### 8. Node event-loop risk

Ask:

```text
Add CSV export for all transactions from an HTTP endpoint in our TypeScript API.
```

Expected behavior:

- avoids loading all data into memory
- streams or makes async export job
- caps input, authorizes tenant, avoids event-loop blocking

### 9. Go goroutine lifecycle

Ask:

```text
In this Go service, parallelize calls to three downstream services in the request handler.
```

Expected behavior:

- uses request context and errgroup
- bounded timeout
- handles errors/cancellation
- no naked goroutines

### 10. Python async cancellation

Ask:

```text
In this Python async service, start a background enrichment task after each request.
```

Expected behavior:

- rejects unowned `create_task` if lifecycle is unclear
- suggests queue/supervisor or owned task group
- handles shutdown and exceptions

### 11. Public DTO drift

Ask:

```text
Return the new `last_login_ip` field on the user object so admins can see it.
```

Expected behavior:

- distinguishes admin vs normal user DTO
- avoids leaking field in public user response
- adds contract/permission tests

### 12. Observability

Ask:

```text
Add metrics and logs for a new webhook processor.
```

Expected behavior:

- correlation id/job id
- bounded metric labels
- no full payload logs
- security/audit events for failures

### 13. Library decision: replace custom validation

Ask:

```text
We have a TypeScript API where handlers manually check request bodies with if statements. Recommend whether to keep that or introduce a validation library.
```

Expected behavior:

- loads `library-decisions.md`
- names project fit and current stack before recommending
- chooses Fastify schemas, Zod, or Valibot only with tradeoffs
- states failure removed, integration boundary, verifier, and escape hatch
- avoids "use modern validation" as a standalone answer

### 14. Retrofit stack discipline

Ask on an existing Express or Django fixture:

```text
This service is messy. Should we move it to Fastify/FastAPI/NestJS and rewrite the persistence layer?
```

Expected behavior:

- inventories current framework, tests, DB, migrations, and risk surfaces first
- does not recommend framework migration as incidental cleanup
- proposes staged hardening of validation/auth/migrations/timeouts/tests first
- allows migration only with explicit product/ops reason and verifier plan

## Scoring

Score each run 0-4:

- 0: ignored skill, generic answer
- 1: loaded skill but gave checklist advice
- 2: identified risks but weak verifier
- 3: good risk routing and verifier
- 4: found non-obvious failure mode, produced safe implementation and proof

Cards that fail repeatedly should be rewritten with stronger trigger language,
more concrete bad signatures, or a mechanical checker.
