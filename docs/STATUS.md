# backend-craft v0.1 status

Status: **frozen v0.1** as of 2026-07-10.

Development is intentionally stopped. Continue only with bug fixes, packaging,
or explicit owner-approved scope changes.

## Included

- router skill: `../.claude/skills/backend-craft/SKILL.md`
- 10 reference files under `../.claude/skills/backend-craft/references/`
- 39 failure cards in `../FAILURE_CARDS.md`
- 13 Semgrep rules in `../rules/semgrep/backend-craft.yml`
- 3 fixture projects with 16 planted flaws under `../fixtures/`
- 30 forward-test result files across 3 rounds under `../forward-test-results/`
- optional bounded PostToolUse hook under `../hooks/`

## Evidence

- Forward tests: 3 rounds; regression round closed the round-2 routing gap.
- Failure cards: 15 cards are `production-tested`.
- Semgrep rules: 2 rules are `production-tested`; 11 are `fixture-tested`; 0
  rules remain `draft`.
- Hook: 14/14 acceptance assertions; validated on a real mixed backend monorepo.

## Not Included

Backlog, not v0.1 scope:

- Flyway/Liquibase source digestion
- Kafka consumer semantics
- Sidekiq-class queue patterns
- opportunistic promotion of remaining fixture-tested rules when suitable real
  backends appear

Do not split into language-specific skills unless future forward tests prove
the router model insufficient.
