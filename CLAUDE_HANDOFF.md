# Handoff for Claude Code

You are continuing the backend-craft package in:

```text
/Users/oleg/Desktop/backend-skills
```

## Current state

Created:

- `SOURCES.md`
- `FAILURE_CARDS.md`
- `SKILL_ARCHITECTURE.md`
- `FORWARD_TESTS.md`
- `.claude/skills/backend-craft/SKILL.md`
- `.claude/skills/backend-craft/references/*.md`
- `.claude/skills/backend-craft/references/library-decisions.md`
- `.claude/skills/backend-craft/references/stack-recipes.md`

Do not revert these. The package intentionally moved away from the earlier
"seven large skills" plan and toward one router skill with risk-domain
references.

## Objective

Turn backend-craft into a production-useful skill package, not a checklist.
Everything should be framed as:

```text
situation -> common agent failure -> blast radius -> safe pattern -> verifier -> escape hatch
```

The skill now includes a library/stack decision layer. Do not replace it with a
generic "use modern libraries" list. For every library recommendation, preserve
the gate:

```text
current project fit -> failure removed -> integration boundary -> verifier -> escape hatch
```

If exact package APIs, versions, security settings, or "latest" recommendations
matter, check official docs or the installed lockfile before editing. Do not
rewrite dependency guidance from memory.

## Next tasks

### 1. Forward-test the skill — DONE (round 1, 2026-07-10)

14/14 prompts run blind via subagents with separate judges; results in
`forward-test-results/` (mean 3.86/4). Skill/reference/card fixes from the
misses are applied; 13 cards promoted to `production-tested`.

Round 2 remains: rerun with isolated (copied) fixtures per the new isolation
rules in `FORWARD_TESTS.md` to confirm the routing fixes close the 004
(transaction-around-payment) and 008 (unbounded export) misses. Never let a
tested agent edit the shared fixtures — round 1 contaminated them and they had
to be restored from builder transcripts (see CHANGELOG.md).

### 2. Rule packs — DONE for the high-confidence set (2026-07-10)

`rules/semgrep/backend-craft.yml` is fixture-tested: 13/13 detectable plants
caught, 0 false positives on clean contrast code (run command and verification
record in `CHECKERS.md`). The TS floating-promise Semgrep rule was retired —
Semgrep matches subexpressions and cannot anchor JS statements; the card's
verifier is type-aware `@typescript-eslint/no-floating-promises`.
"Public route returning ORM/entity directly" was skipped: no stable mechanical
signature.

Remaining: validate the pack on at least one real backend, then promote rule
statuses from `fixture-tested` to `production-tested`.

### 3. Fixture projects — DONE (2026-07-10)

`fixtures/{python-fastapi,go-http,ts-fastify}` exist: 15 planted flaws total,
each mapped to a card and marked `PLANTED: <card-id>`, happy-path suites green,
per-fixture READMEs list expected failures. `fixtures/README.md` has the
acceptance procedure. Treat the current tree as the pristine baseline; snapshot
before any forward-test run.

### 4. Implement a bounded hook — NOW UNBLOCKED

The rule corpus is now proven on fixtures. When implementing:

- project-local tools first (`uv run`, `poetry run`, `go test`, `pnpm exec`, `npm exec`, etc.)
- max 5 findings
- dedup within session
- always exit 0
- one-time warning when no project-local checker exists
- never treat clean lint as "backend safe"

### 5. Continue source digestion

Use `SOURCES.md`. Add sources only when they produce a card, verifier, or
checker. Do not paste broad documentation into the skill.

High-value missing source areas:

- Go `net/http` server timeout docs
- Flyway or Liquibase docs if Java/JVM migration coverage becomes necessary
- Kafka consumer semantics if event-stream services enter scope
- Sidekiq-like patterns if Ruby/Rails services enter scope
- framework-specific auth docs for the fixture stacks after fixtures exist
- official docs for any new library added to `library-decisions.md`

## Writing rules

- Keep `SKILL.md` short.
- Put details in `references/`.
- Add concrete bad signatures.
- Add a verifier for every rule.
- Add escape hatches to avoid cargo-cult behavior.
- Do not split into language-specific skills until forward tests prove it is
  necessary.
