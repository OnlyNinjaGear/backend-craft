# backend-craft

[![CI](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml)
![Channel](https://img.shields.io/badge/channel-main-blue)
![Readiness](https://img.shields.io/badge/readiness-team%20pilot-yellowgreen)
![Rules](https://img.shields.io/badge/semgrep-16%20rules-2ea44f)
![Fixtures](https://img.shields.io/badge/fixtures-16%20planted%20flaws-orange)

`backend-craft` is a Claude Code/Codex skill package for backend engineering.
It is designed to stop agents from shipping plausible backend code that fails
under production conditions.

It is not a style guide and not a language encyclopedia. The skill routes work
by **failure surface** first:

- API contracts and compatibility
- authorization, tenancy, PII, secrets, SSRF
- persistence, migrations, transactions, indexes
- retries, timeouts, queues, workers, cancellation, idempotency
- observability, tests, CI, review discipline
- Python, Go, and TypeScript/Node language adapters

Current channel: **post-v0.1 `main` snapshot**. The immutable `v0.1` tag predates
the latest evidence pack. Scope remains frozen unless explicitly reopened.

## Can I Use It Now?

Yes. The current `main` snapshot is usable for a **team pilot** on new and
existing backend projects. Frozen means the scope is controlled, not that the
skill is unfinished.

| Surface | State | Evidence |
|---|---|---|
| Router and four work modes | Ready | Start, Retrofit, Harden, and Continue passed blind tests |
| Python + FastAPI | Validated representative stack | 5 planted flaws plus Python async and observability forward tests |
| Go + `net/http` | Validated representative stack | 6 planted flaws plus concurrency and payment forward tests |
| TypeScript + Fastify | Validated representative stack | 5 planted flaws plus export, DTO, and rewrite forward tests |
| NestJS | Observed on real code | checker and hook run on a mixed monorepo; no dedicated fixture |
| PostgreSQL | Partially validated | guidance, migration tests, and a reducer; one verifier still has timing debt |
| MongoDB, Django/DRF, Redis/BullMQ | Documented only | sources and recipes exist; dedicated fixtures and blind tests do not |
| Kafka, RabbitMQ, Kubernetes | Outside v0.1 | no support claim |

This is evidence for representative stacks and production failure surfaces,
not a claim that an entire language is "100% covered." See the
[readiness dashboard](docs/STATUS.md) for release gates and the next work queue.

## What Is Included

```text
.claude/skills/backend-craft/      # the installable skill
  SKILL.md                         # router workflow
  references/                      # risk-domain reference packs
rules/semgrep/backend-craft.yml    # high-confidence Semgrep checks
hooks/                             # optional bounded PostToolUse hook
fixtures/                          # intentionally flawed backend fixtures
forward-test-results/              # skill evaluation transcripts
docs/                              # architecture, evidence, source map
FAILURE_CARDS.md                   # failure-card corpus
```

## Install The Skill

Use it as a project-local Claude Code skill:

```bash
mkdir -p /path/to/your-project/.claude/skills
cp -R .claude/skills/backend-craft /path/to/your-project/.claude/skills/
```

The Semgrep pack (`rules/`) and the hook (`hooks/`) live outside the skill
directory and are copied separately — you only need them if you want the
mechanical checks and post-edit hints. The skill itself works without them.

Then ask Claude Code to use `backend-craft` when building, reviewing, hardening,
or choosing a backend stack.

Example prompts:

```text
Use backend-craft to review this backend for production risks.
```

```text
Use backend-craft to design the backend foundation for a small B2B SaaS.
```

```text
Use backend-craft while adding this mutating endpoint. Clients may retry.
```

## Optional Hook

The optional hook runs cheap file-level checks after edits and feeds at most
five advisory findings back to the agent. It always exits `0` and never claims a
clean checker run means the backend is safe.

See [hooks/README.md](hooks/README.md).

## Validation Status

The current `main` snapshot contains:

- 41 failure cards, including 15 `production-tested` cards
- 16 Semgrep rules: 2 `production-tested`, 11 `fixture-tested`, 3 `draft`
- 3 runnable fixture projects with 16 planted flaws
- 3 rounds of forward tests
- real-backend validation on a mixed NestJS/Go/Python monorepo
- a bounded hook with 14/14 acceptance assertions

Status details live in [docs/CHECKERS.md](docs/CHECKERS.md) and
[docs/EVIDENCE_LOG.md](docs/EVIDENCE_LOG.md).

## Run Checks Locally

Repository sanity checks:

```bash
uv run --with pyyaml python scripts/validate_repo.py
```

Fixture suites:

```bash
cd fixtures/python-fastapi && uv run pytest -q
cd ../go-http && go vet ./... && go test ./...
cd ../ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test
```

Semgrep pack:

```bash
uvx semgrep --config rules/semgrep/backend-craft.yml --no-git-ignore --exclude node_modules .
```

Hook acceptance tests:

```bash
hooks/test-hook.sh
```

## Documentation

- [docs/STATUS.md](docs/STATUS.md) — readiness, coverage matrix, and release gates
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — skill architecture and routing model
- [FAILURE_CARDS.md](FAILURE_CARDS.md) — failure-card corpus
- [docs/CHECKERS.md](docs/CHECKERS.md) — checker status and validation records
- [docs/SOURCES.md](docs/SOURCES.md) — admitted source map
- [docs/FORWARD_TESTS.md](docs/FORWARD_TESTS.md) — forward-test protocol
- [docs/EVIDENCE_LOG.md](docs/EVIDENCE_LOG.md) — evidence/promotion log
- [fixtures/README.md](fixtures/README.md) — fixture corpus

## Development Boundary

Do not expand the skill casually. New material should enter only when it can
produce a failure card, verifier, checker, or source-backed playbook step.

Backlog items are intentionally deferred:

- Flyway/Liquibase source digestion
- Kafka consumer semantics
- Sidekiq-class queue patterns
- dedicated Redis/BullMQ runtime semantics
- Kubernetes and deployment-platform scope
- dedicated MongoDB and Django/DRF fixtures
- opportunistic promotion of remaining fixture-tested Semgrep rules

Do not split this into language-specific skills unless future forward tests
prove the router insufficient.
