---
name: backend-craft
description: Use for backend engineering work in Python, Go, TypeScript/Node, Postgres, MongoDB, API design, auth, migrations, queues, workers, reliability, observability, testing, framework/library selection, code review, hardening existing services, starting a new backend, or auditing a backend project. Use when changes may affect API contracts, data persistence, authorization, tenant boundaries, retries, timeouts, side effects, migrations, background jobs, dependencies, or production operations.
---

# backend-craft

Backend safety skill for building, retrofitting, and hardening services. This
skill is not a style guide. It is a workflow for preventing common production
failures.

Source and updates: https://github.com/OnlyNinjaGear/backend-craft — current
version in `.claude-plugin/plugin.json` next to this file (plugin installs)
or in the repo's `v*` git tags. To update: `/plugin marketplace update
backend-craft-marketplace` (plugin install), or `git pull` + re-copy
`.claude/skills/backend-craft/` over this folder (manual/raw install).

## Operating rule

Do not start with language advice. Start with blast radius.

Before code, perform an Impact Read:

1. What public contracts can change?
2. What data can be read, written, deleted, or migrated?
3. What principal, permission, or tenant boundary is involved?
4. What side effects can repeat, partially fail, or outlive the request?
5. What existing tests/checkers prove this surface?

If the answer is "none", state the narrow scope and proceed with ordinary
codebase-fit behavior. If any answer is non-empty, load the relevant reference
file below.

## Modes

### Start mode

Use when the user is starting a backend or asks for the best setup.

Deliver:

- stack choice with tradeoffs
- dependency/library defaults with a verifier for each non-trivial choice
- API contract strategy
- auth/tenant model
- database and migration strategy
- reliability defaults: timeouts, retries, idempotency, queues
- observability baseline
- test and CI baseline
- first irreversible decisions and how to delay them

Read:

- `references/stack-recipes.md`
- `references/library-decisions.md`
- `references/api-contracts.md`
- `references/auth-tenancy-security.md`
- `references/persistence-migrations.md`
- `references/reliability-async.md`
- `references/observability-ops.md`
- `references/testing-verification.md`
- `references/language-adapters.md`

### Retrofit mode

Use when attaching to existing backend code.

Deliver:

- inventory of framework, package manager, DB, migration system, tests, CI
- risk map ordered by blast radius
- staged hardening plan that preserves behavior; always include the server
  baseline (request/connection timeouts, body-size limits) even when no
  specific flaw was found
- project-local commands using the package manager detected from the lockfile
  (pnpm test, not npm test, when `pnpm-lock.yaml` exists)

When the plan prescribes new tests or CI gates, load
`references/testing-verification.md` before writing the verifier plan.

Read `references/codebase-fit.md` first, then load risk references based on
the inventory.

### Harden mode

Use for review, audit, or "bring this backend to production quality".

Deliver findings first, ordered by severity. Each finding must include file:line,
failure pattern, blast radius, fix shape, and verifier. Do not invent findings
for coverage optics.

Read all risk references that match changed or inspected surfaces.

### Continue mode

Use for ordinary backend feature or bug-fix work. Run the Impact Read, load only
the needed references, implement, then verify. When the work prescribes or
writes new tests or CI gates, load `references/testing-verification.md` before
writing the verifier plan (same rule as Retrofit mode).

## Reference routing

One change often matches several rows. Load every matched row, not the first —
a concurrency change that also adds a response field triggers both
`reliability-async.md` and `api-contracts.md`.

Routing is not a one-shot decision at the start. Before the final response,
re-scan the actual diff against this table: every row the diff matches must
have its reference in your files-read list, including rows that only started
matching mid-task (e.g. a SQL fix discovered while writing tests).

| Signal | Read |
|---|---|
| endpoint, schema, status code, DTO, response field added/removed, webhook, public response | `references/api-contracts.md` |
| auth, role, permission, tenant, PII, secret, SSRF, user-facing email/SMS/push | `references/auth-tenancy-security.md` |
| SQL, ORM, Mongo, migration, transaction, index, query performance, payment, money movement, DB write paired with an external call, fixing SQL injection / parameterizing queries | `references/persistence-migrations.md` |
| retry, timeout, queue, worker, cron, webhook, cancellation, external API, export, CSV/bulk download, streaming response, fire-and-forget or floating promise, event loop | `references/reliability-async.md` |
| logs, metrics, traces, alerts, runbooks, correlation ids | `references/observability-ops.md` |
| tests, CI, contract testing, DB integration tests, adding or writing any new test file, regression tests for a fix | `references/testing-verification.md` |
| refactor, architecture, naming, module boundaries | `references/codebase-fit.md` |
| new service, stack choice, scaffold, project setup | `references/stack-recipes.md` |
| framework choice, dependency choice, library replacement, custom code vs library | `references/library-decisions.md` |
| Python, Go, TypeScript/Node idioms or tool rules | `references/language-adapters.md` |

## Final proof contract

For backend work that changes behavior, final response must cite at least one
of:

- test name and result
- type/lint/check command and result
- migration dry run or rollback proof
- OpenAPI/contract diff result
- query plan/query count proof
- explicit reason the work is untestable in the current environment

Running a command whose output you did not inspect does not count. Before
reporting, re-verify the "files changed" list against the working tree —
signatures, arity, and new-vs-modified status must match reality, not memory.
If the change adds or modifies tests, `references/testing-verification.md`
must appear in the files you read. If the change adds, fixes, or parameterizes
SQL/query construction, `references/persistence-migrations.md` must appear in
the files you read.

## Severity guide

- P0: data loss, auth bypass, tenant leak, duplicate money/order side effect,
  irreversible unsafe migration, deploy-blocking contract break
- P1: production outage risk, retry storm, unbounded worker concurrency, broken
  rollback, missing critical test for changed behavior
- P2: maintainability or reliability issue likely to cause future defects
- P3: style or local cleanup with low production risk

Approve only when no P0/P1 issues remain and changed behavior has proof.

## Contributing a case (opt-in, off by default)

After work that surfaces a *generalizable, repeatable* failure mode — useful to
other projects, not a bug specific to this codebase — you may offer once to
contribute an anonymized case to backend-craft. The strongest source is an agent
miss caught by a reviewer or test (e.g. Codex correcting the agent): capture the
transferable lesson, not process nitpicks. This is opt-in: never send anything
without the user's explicit confirmation, always under the user's own GitHub
account, and only after showing the exact anonymized text. If the user shows
interest, load `references/contribute-case.md` and follow it exactly. Do not
offer for codebase-specific bugs, process/tooling nitpicks, or anything you
cannot fully anonymize.
