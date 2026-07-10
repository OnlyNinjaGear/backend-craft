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
- fixture projects (3 stacks, 15 planted flaws): [`fixtures/`](fixtures/)
- forward-test results (round 1, 2026-07-10, mean 3.86/4): [`forward-test-results/`](forward-test-results/)
- evidence log: [`CHANGELOG.md`](CHANGELOG.md)

Status (2026-07-10):

- 14/14 forward tests run blind with separate judges; 13 cards promoted to
  `production-tested` with test ids in their Status lines
- Semgrep pack executed and narrowed against a probe corpus + fixtures:
  13/13 detectable plants caught, 0 false positives; the TS floating-promise
  rule was retired in favor of type-aware eslint (see CHECKERS.md)
- forward-test isolation rules added after tested agents mutated fixtures
  in place (see CHANGELOG.md and FORWARD_TESTS.md)

Not done yet:

- no hook script yet (rule corpus now proven enough to start)
- Semgrep pack not yet validated on a real backend (`production-tested` for
  rules requires one)

## Next build order

1. Implement the bounded hook (project-local tools first, max 5 findings,
   dedup, always exit 0 — see CLAUDE_HANDOFF.md task 4).
2. Validate the Semgrep pack on at least one real backend; promote rule
   statuses.
3. Forward-test round 2 with isolated (copied) fixtures to confirm the routing
   fixes from round 1 close the 004/008 misses.
4. Continue source digestion per SOURCES.md high-value gaps.

Do not write large language-specific skills until the failure cards prove what
language-specific knowledge is actually needed.
