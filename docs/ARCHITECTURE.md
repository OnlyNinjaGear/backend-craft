# backend-craft architecture

The package should make backend agents safer by changing their workflow, not by
teaching them slogans. The primary abstraction is not a language. It is a
production failure surface.

## Product shape

Use one router skill plus reference packs:

```text
.claude/skills/backend-craft/
├── SKILL.md
└── references/
    ├── api-contracts.md
    ├── persistence-migrations.md
    ├── auth-tenancy-security.md
    ├── reliability-async.md
    ├── observability-ops.md
    ├── testing-verification.md
    ├── library-decisions.md
    ├── stack-recipes.md
    ├── codebase-fit.md
    └── language-adapters.md
```

Language knowledge is an adapter, not the top-level split. A Python, Go, or
TypeScript backend can fail in the same way: broken authorization, unsafe
migration, retry storm, queue idempotency bug, missing contract test. The router
loads the risk reference first and the language adapter second.

## Modes

### Start mode

Use when the project is new or the user asks for best stack/setup.

Agent output should include:

- stack choice and tradeoffs
- library/dependency defaults and tradeoffs
- API contract approach
- auth/tenant model
- persistence and migration strategy
- reliability defaults: timeouts, retries, idempotency, queues
- observability baseline
- test/CI baseline
- "first irreversible decision" warnings

### Retrofit mode

Use when attaching to existing code.

Agent output should include:

- inventory of frameworks, package manager, DB, migrations, tests, CI
- changed/owned surfaces
- P0/P1 risk map before refactor suggestions
- staged hardening plan that preserves behavior
- project-local check commands

### Harden mode

Use when auditing or improving the whole backend.

Agent output should include:

- findings ordered by blast radius
- each finding cites file:line and failure card
- minimal patch plan
- verifier for every changed behavior
- remaining risks that need product/ops input

### Continue mode

Use during ordinary feature work after setup.

Agent must run the Impact Read, load only relevant reference packs, implement,
then prove behavior with tests/checks.

## Impact Read

Before code, write one concise paragraph or internal note answering:

1. What public contracts can change?
2. What data can be read/written/deleted?
3. What principal/tenant/permission boundary is involved?
4. What side effects can repeat or partially fail?
5. What existing tests/checkers prove the surface?

If none apply, state why. If any apply, load the matching reference pack.

## Reference loading

| Impact signal | Read |
|---|---|
| endpoint, schema, status code, public DTO, webhook | `api-contracts.md` |
| auth, ownership, role, tenant, PII, SSRF, secret | `auth-tenancy-security.md` |
| SQL, ORM, Mongo, migration, transaction, index | `persistence-migrations.md` |
| retry, timeout, queue, worker, cron, cancellation, external API | `reliability-async.md` |
| logs, metrics, traces, alerts, runbook | `observability-ops.md` |
| tests, CI, contract tests, database tests | `testing-verification.md` |
| new service, stack choice, scaffold, project setup | `stack-recipes.md` |
| framework choice, dependency choice, custom code vs library | `library-decisions.md` |
| architecture/naming/refactor/module boundaries | `codebase-fit.md` |
| Python, Go, TypeScript/Node idioms | `language-adapters.md` |

## Rule quality bar

A rule is allowed into a reference only when it has:

- trigger: when the agent should apply it
- failure signature: what bad code looks like
- blast radius: what production failure it prevents
- safe pattern: concrete implementation shape
- verifier: a test/check/log/trace/diff/query plan
- escape hatch: when the rule should not fire
- source or observed incident

Reject rules that only say "do X well" or "avoid Y".

## Checker strategy

Use layers:

1. Project-local tools first: existing test/lint/type commands.
2. Contract tools when present: OpenAPI diff, Pact, generated clients.
3. DB tools when relevant: migration dry run, EXPLAIN, query count tests.
4. Lightweight structural checks: Semgrep or ast-grep for high-confidence failure signatures.
5. LLM reviewer only after deterministic evidence is gathered.

Do not let a clean linter mean "backend is safe." Linters are syntax and local
bug filters; the expensive failures are usually semantic.

## Knowledge acquisition backlog

To keep improving the package, collect:

- real failures from agent-written backend changes
- real code review comments from senior backend engineers
- migration incident writeups
- API compatibility incidents
- security review findings
- production retry/queue/idempotency incidents

Convert each into a failure card before adding prose to a skill.
