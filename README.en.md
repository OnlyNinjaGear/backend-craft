# backend-craft

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

Current release: **v0.1 frozen**. Further source digestion and rule promotion
are backlog work unless explicitly reopened.

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

v0.1 contains:

- 39 failure cards, including 15 `production-tested` cards
- 13 Semgrep rules: 2 `production-tested`, 11 `fixture-tested`, 0 `draft`
- 3 runnable fixture projects with 16 planted flaws
- 3 rounds of forward tests
- real-backend validation on a mixed NestJS/Go/Python monorepo
- a bounded hook with 14/14 acceptance assertions

Status details live in [docs/CHECKERS.md](docs/CHECKERS.md) and
[docs/EVIDENCE_LOG.md](docs/EVIDENCE_LOG.md).

## Run Checks Locally

Repository sanity checks:

```bash
python3 -m pip install pyyaml
python3 scripts/validate_repo.py
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
- opportunistic promotion of remaining fixture-tested Semgrep rules

Do not split this into language-specific skills unless future forward tests
prove the router insufficient.

## License

No open-source license has been selected yet. Choose and add a license before
publishing this repository publicly.
