# backend-craft

[![CI](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml)
![Failure patterns](https://img.shields.io/badge/failure%20patterns-41-4c566a)
![Rules](https://img.shields.io/badge/semgrep-16%20rules-2ea44f)
![Fixtures](https://img.shields.io/badge/fixtures-3%20runnable-d97706)

[Русский](README.md)

A production-risk skill for Claude Code and Codex.

It helps coding agents design, review, and harden backends by checking API
contracts, authorization boundaries, migrations, retries, timeouts,
idempotency, and background jobs before those failures reach production.

**54 failure patterns · 16 Semgrep rules · 3 runnable fixtures · 16 planted flaws**

[Install](#installation) · [Supported stacks](#supported-stacks) ·
[How it works](#how-it-works) · [Project readiness](docs/STATUS.md)

## What Developers Get

| Task | What the skill does |
|---|---|
| New backend | helps choose the stack, libraries, API, data model, migrations, tests, and CI |
| Existing project | reads the code and system boundaries before proposing staged changes |
| New feature | checks contracts, permissions, data, retries, timeouts, and failure paths |
| Review or audit | looks for defects with real blast radius instead of style arguments |
| Library choice | compares risk reduction, adoption cost, and the verification path |

Every material recommendation should end with a test, checker, measurement, or
concrete verification plan.

## Supported Stacks

`Tested` means a dedicated runnable fixture plus blind agent tests. `Real-code
checked` means the tooling was run on a real repository without a dedicated
fixture. `Guidance` means sources and instructions exist, but dedicated
validation does not.

| Language or stack | Level | Evidence |
|---|---|---|
| Python + FastAPI | Tested | fixture with 5 production flaws; async and observability scenarios |
| Go + `net/http` | Tested | fixture with 6 flaws; concurrency, cancellation, and payment scenarios |
| TypeScript + Fastify | Tested | fixture with 5 flaws; DTO, export, and retrofit scenarios |
| NestJS | Real-code checked | checker and hook validated on a real admin API |
| PostgreSQL | Partial | migration scenarios, SQL checks, and a runnable reducer |
| MongoDB, Django/DRF, Redis/BullMQ | Guidance | sources, failure cards, and stack recipes without dedicated fixtures |

Kafka, RabbitMQ, and Kubernetes are outside the current scope. See the
[readiness dashboard](docs/STATUS.md) for the complete evidence matrix and
release gates.

## How It Works

The skill starts from the failure surface, not the language. It identifies what
can change, loads only the matching reference packs, and verifies the result.

| Mode | When it runs | Output |
|---|---|---|
| **Start** | a backend begins from zero | stack, contracts, data, auth, reliability, tests, and CI foundation |
| **Retrofit** | the backend already exists | inventory, P0/P1 risk map, and a staged hardening plan |
| **Harden** | the whole backend needs an audit | findings by blast radius, minimal patches, and a verifier per change |
| **Continue** | a feature or bugfix is in progress | impact read, scoped implementation, and proof of changed behavior |

## Example Prompts

```text
Use backend-craft to design the backend foundation for a small B2B SaaS.
```

```text
Use backend-craft to review this existing backend for production risks.
Do not rewrite it; give me a staged hardening plan.
```

```text
Use backend-craft while adding this mutating endpoint. Clients may retry.
```

```text
Use backend-craft to review this pull request. Prioritize auth, data integrity,
failure handling, and missing verification.
```

## Installation

Via the plugin marketplace (recommended — gives you auto-updates):

```
/plugin marketplace add OnlyNinjaGear/backend-craft
/plugin install backend-craft@backend-craft-marketplace
```

Update: `/plugin marketplace update backend-craft-marketplace`, or wait for
the auto-update notice and run `/reload-plugins`.

Manual install (no auto-updates, if the marketplace is unreachable):

```bash
git clone https://github.com/OnlyNinjaGear/backend-craft.git
mkdir -p /path/to/your-project/.claude/skills
cp -R backend-craft/.claude/skills/backend-craft \
  /path/to/your-project/.claude/skills/
```

The skill works without extra tooling. The Semgrep pack and PostToolUse hook
are installed separately.

## Failure Surfaces

| Area | Typical risks |
|---|---|
| API | contract drift, DTO leaks, incorrect status codes, unsafe webhooks |
| Auth and tenancy | BOLA, missing tenant filters, roles, PII, secrets, SSRF |
| Data | SQL injection, transactions around network calls, migrations, indexes, N+1 |
| Reliability | retry storms, missing jitter/caps, timeout leaks, cancellation, duplicate delivery |
| Queues and workers | idempotency, poison messages, unbounded concurrency, shutdown |
| Observability | correlation, cardinality, redaction, failures without a signal |
| Verification | happy-path-only tests, DB integration, contract diffs, migration proof |
| Languages | Python async/exceptions, Go contexts/goroutines/errors, Node runtime boundaries |

## Why Trust It

The current snapshot contains 54 failure cards, including 17
`production-tested` cards, and 16 Semgrep rules.

| Artifact | Current state |
|---|---:|
| Failure cards | 54 |
| Semgrep rules | 16 |
| Rules: `production-tested` | 2 |
| Rules: `fixture-tested` | 11 |
| Rules: `draft` | 3 |
| Fixtures | 3 projects, 16 planted flaws |
| Forward tests | 3 rounds, 30 result files |
| Real-code validation | mixed NestJS/Go/Python monorepo |
| Hook acceptance | 14/14 assertions |

The fixtures look like ordinary green backends: they build and pass happy-path
tests while retaining production-safety defects. Fresh agents receive tasks
without the answer key, and separate judges evaluate their results.

[Readiness dashboard](docs/STATUS.md) · [Evidence log](docs/EVIDENCE_LOG.md) ·
[Forward-test protocol](docs/FORWARD_TESTS.md)

## Optional Tooling

| Component | Purpose |
|---|---|
| [Semgrep pack](rules/semgrep/backend-craft.yml) | catches 16 high-confidence syntax patterns |
| [PostToolUse hook](hooks/README.md) | surfaces up to 5 advisory findings after an edit without blocking the agent |
| [Failure cards](FAILURE_CARDS.md) | record trigger, blast radius, safe pattern, verifier, and escape hatch |
| [Fixtures](fixtures/README.md) | reproduce common defects and false-positive boundaries |

A clean checker run is not proof that a backend is safe. Semantic failures such
as BOLA or broken idempotency still require tests and review.

## Project Status

The current `main` snapshot is ready for a team pilot. Scope is controlled: new
topics require a concrete failure signal and a verifiable result. Tag history,
coverage levels, and the finite next-release queue live in
[docs/STATUS.md](docs/STATUS.md).

## Contributing

Useful contributions are narrow and testable:

- an anonymized production bug with a reducer;
- an official source that implies a concrete verifier;
- a checker with true-positive and false-positive boundaries;
- a runnable fixture;
- a blind forward test.

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the
[contributor guide](docs/CONTRIBUTOR_GUIDE.md). Architecture, sources, and
maintenance rules are indexed under [docs/](docs/README.md).

## What This Project Does Not Claim

- it does not make every backend production-ready with one prompt;
- one tested framework does not prove complete language coverage;
- it does not replace project-local tests, linters, security review, or team experience.
