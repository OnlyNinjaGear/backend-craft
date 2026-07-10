# backend-craft

`backend-craft` is a backend skill package for Claude Code/Codex-style agents.
Its goal is not to repeat "write good backend code". Its goal is to prevent the
production failures agents are most likely to introduce while building,
retrofitting, or hardening backend services.

Supported focus areas:

- Python, Go, TypeScript/Node
- Postgres, MongoDB
- API contracts, auth, tenancy, security
- migrations, transactions, indexes
- retries, timeouts, queues, workers, idempotency
- observability, tests, CI, review

## Current direction

The earlier plan split the package into seven large skills:

- `backend-philosophy`
- `clean-code`
- `database-backend`
- `backend-reviewer`
- `python-backend`
- `go-backend`
- `ts-backend`

That shape is understandable, but it pushes the project toward a typical
checklist/wiki. The current direction is different:

```text
.claude/skills/backend-craft/
├── SKILL.md                         # router skill
└── references/
    ├── api-contracts.md
    ├── auth-tenancy-security.md
    ├── persistence-migrations.md
    ├── reliability-async.md
    ├── observability-ops.md
    ├── testing-verification.md
    ├── library-decisions.md
    ├── stack-recipes.md
    ├── codebase-fit.md
    └── language-adapters.md
```

The top-level split is by production failure surface, not language. Language
rules are adapters loaded after the relevant risk domain.

## Modes

### Start mode

For a new backend or stack choice. Produces architecture defaults for API
contracts, auth/tenant model, database/migrations, library choices, reliability,
observability, tests, and CI.

### Retrofit mode

For attaching to an existing backend. Inventories framework, package manager,
DB, migrations, tests, CI, and produces a staged hardening plan.

### Harden mode

For reviewing or improving an entire backend. Findings are ordered by blast
radius and require file:line, failure card, fix shape, and verifier.

### Continue mode

For ordinary feature work. The agent runs an Impact Read, loads only relevant
references, implements, then proves the changed behavior.

## Knowledge model

The atomic unit is a **failure card**, not a best-practice paragraph.

Each card has:

- trigger
- model failure
- blast radius
- detection signature
- safe pattern
- verifier
- escape hatch
- sources

See [`FAILURE_CARDS.md`](FAILURE_CARDS.md).

## Source map

Primary sources are tracked in [`SOURCES.md`](SOURCES.md). A source is admitted
only if it can produce a failure card, playbook step, or checker. Current source
families include OWASP, OpenAPI/JSON Schema, Google AIP, Stripe idempotency,
Google SRE, AWS/Azure reliability patterns, PostgreSQL, MongoDB, Python, Go,
Node/TypeScript, FastAPI, Django/DRF, SQLAlchemy/Alembic, Pydantic, chi, pgx,
sqlc, Fastify, NestJS, Zod, Drizzle, Kysely, Prisma, BullMQ, Semgrep, ast-grep,
CodeQL, Pact, Testcontainers, and oasdiff.

## Implementation status

Created:

- router skill: [`.claude/skills/backend-craft/SKILL.md`](.claude/skills/backend-craft/SKILL.md)
- risk references: [`.claude/skills/backend-craft/references/`](.claude/skills/backend-craft/references/)
- library decision layer: [`.claude/skills/backend-craft/references/library-decisions.md`](.claude/skills/backend-craft/references/library-decisions.md)
- stack recipes: [`.claude/skills/backend-craft/references/stack-recipes.md`](.claude/skills/backend-craft/references/stack-recipes.md)
- source map: [`SOURCES.md`](SOURCES.md)
- initial failure-card corpus: [`FAILURE_CARDS.md`](FAILURE_CARDS.md)
- architecture notes: [`SKILL_ARCHITECTURE.md`](SKILL_ARCHITECTURE.md)
- forward-test prompts: [`FORWARD_TESTS.md`](FORWARD_TESTS.md)
- handoff instructions: [`CLAUDE_HANDOFF.md`](CLAUDE_HANDOFF.md)
- checker notes: [`CHECKERS.md`](CHECKERS.md)
- Semgrep rules (fixture-tested): [`rules/semgrep/backend-craft.yml`](rules/semgrep/backend-craft.yml)
- fixture projects (3 stacks, 16 planted flaws): [`fixtures/`](fixtures/)
- forward-test results (round 1, 2026-07-10, mean 3.86/4): [`forward-test-results/`](forward-test-results/)
- evidence log: [`CHANGELOG.md`](CHANGELOG.md)

Status (2026-07-10):

- forward-test round 1: 14/14 blind tests, mean 3.86/4; routing fixes applied
  from the misses
- forward-test round 2 (isolated fixture copies, leak-stripped): mean 3.93/4,
  13/14 round-1 misses closed — both round-1 3-scores (payment transaction
  boundary, unbounded CSV export) fixed by the routing changes; one new
  routing-discipline gap (testing-verification.md) fixed in SKILL.md
- forward-test round 3 (regression round): both 114-style tasks 4/4 with the
  round-2 regression closed; proof-contract hard gates generalized (SQL gate +
  pre-report diff-vs-routing-table re-scan)
- 15 cards `production-tested` with test ids in their Status lines
- Semgrep pack executed and narrowed against a probe corpus + fixtures:
  13/13 detectable plants caught, 0 false positives; the TS floating-promise
  rule was retired in favor of type-aware eslint; the two later-added Go
  server-timeout rules promoted `draft` → `fixture-tested` on 2026-07-10 via a
  go-http fixture plant (`ops.go`, 2/2 caught, 0 FP); see CHECKERS.md
- pack + hook validated on a real monorepo (henry: NestJS admin API, Go
  Temporal workers, Python workers): 49 findings sample-verified, 0
  wrong-match FPs; two rules with real TPs promoted to production-tested;
  one monorepo hook bug found and fixed (eslint/lockfile at workspace root)
- repo is now a git repository; fixtures protected by baseline commit
- forward-test isolation rules added after round-1 tested agents mutated
  fixtures in place (see CHANGELOG.md and FORWARD_TESTS.md)

Also done:

- bounded PostToolUse hook: [`hooks/`](hooks/) — project-local tools first,
  max 5 findings, session dedup, always exit 0, never claims safety;
  14/14 acceptance assertions

Not done yet:

- most rules are `fixture-tested`, not `production-tested`: the henry run
  produced real TPs only for `sync-fs-in-code` and `swallowed-exception-pass`;
  the rest ran clean there (FN-probes confirmed true negatives), so they wait
  for a real backend that actually contains their target constructs

## Next build order

1. Continue source digestion per SOURCES.md high-value gaps.
2. Promote remaining rules to `production-tested` opportunistically — when a
   real backend with their target constructs shows up, not by hunting for one.
3. Do not split into language-specific skills unless future forward tests
   prove the router insufficient.

Do not write large language-specific skills until the failure cards prove what
language-specific knowledge is actually needed.
