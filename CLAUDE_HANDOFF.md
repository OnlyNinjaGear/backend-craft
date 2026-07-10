# Handoff for Claude Code

**FROZEN at v0.1 (2026-07-10, owner decision).** Development is stopped.
Backlog (do NOT do unless the owner explicitly reopens work): source
digestion (Flyway/Liquibase, Kafka, Sidekiq-class patterns), promotion of
remaining rules to `production-tested`. Bug fixes on request only.

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

Round 2 — DONE (2026-07-10): rerun on disposable copies with grading markers
stripped; mean 3.93/4, 13/14 round-1 misses closed. Both round-1 3-scores
(104 transaction-around-payment, 108 unbounded export) fixed by the routing
changes and re-proven. One new gap (test-writing without
testing-verification.md) fixed via routing signals + proof-contract clause.
Results in `forward-test-results/1xx-*.md`. Repo is now git — snapshot/restore
is `git status` + `git checkout` instead of transcript reconstruction.

Round 3 — DONE (2026-07-10): 301 write-tests + 302 rewrite-retest, both 4/4,
regression closed (testing-verification.md loaded in both; new SQL signal
fired in 302). 301 exposed the mid-task routing gap-class; fixed via SQL hard
gate in the proof contract + mandatory pre-report diff-vs-routing re-scan.
Results in `forward-test-results/30x-*.md`.

### 2. Rule packs — DONE for the high-confidence set (2026-07-10)

`rules/semgrep/backend-craft.yml` is fixture-tested: 13/13 detectable plants
caught, 0 false positives on clean contrast code (run command and verification
record in `CHECKERS.md`). The two later-added Go server-timeout rules were
promoted `draft` → `fixture-tested` on 2026-07-10 via a go-http fixture plant
(`ops.go`: bare `&http.Server` ops listener + package-level `ListenAndServe`
debug listener; 2/2 caught, probe corpus 4 TP / 0 FP; promotion record in
`CHECKERS.md`). Real-backend validation (henry monorepo, 2026-07-10):
`sync-fs-in-code` and `swallowed-exception-pass`
promoted to `production-tested` on real true positives; remaining rules ran
clean with FN-probes confirming the repo has no target constructs. The TS floating-promise Semgrep rule was retired —
Semgrep matches subexpressions and cannot anchor JS statements; the card's
verifier is type-aware `@typescript-eslint/no-floating-promises`.
"Public route returning ORM/entity directly" was skipped: no stable mechanical
signature.

Remaining: promote the rest of the pack to `production-tested`
opportunistically — henry had no target constructs for those rules, so the
promotion needs a real backend that does. Do not hunt for one; validate when
one shows up.

### 3. Fixture projects — DONE (2026-07-10)

`fixtures/{python-fastapi,go-http,ts-fastify}` exist: 16 planted flaws total
(go-http gained a server-timeout plant in `ops.go`, 2026-07-10), each mapped
to a card and marked `PLANTED: <card-id>`, happy-path suites green,
per-fixture READMEs list expected failures. `fixtures/README.md` has the
acceptance procedure. Treat the current tree as the pristine baseline; snapshot
before any forward-test run.

### 4. Implement a bounded hook — DONE (2026-07-10)

`hooks/backend-craft-check.py` + `hooks/test-hook.sh` (14/14 assertions pass)
+ `hooks/README.md` wiring docs. All six contract points implemented:
project-local first, max 5 findings, session dedup, always exit 0, one-time
no-checker warning, never claims safety. Not wired into this repo's settings
(fixtures are intentionally flawed); consumer projects wire it per README.

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

- Flyway or Liquibase docs if Java/JVM migration coverage becomes necessary
- Kafka consumer semantics if event-stream services enter scope
- Sidekiq-like patterns if Ruby/Rails services enter scope
- official docs for any new library added to `library-decisions.md`

Done 2026-07-10: framework-specific auth docs for the fixture stacks —
FastAPI was already covered; Fastify Hooks + Encapsulation and FastAPI
Bigger Applications digested into the `auth-middleware-scope-miss` card
(Go stdlib has no auth framework docs to digest; the card's Go line covers
mux-wrapping scope). Only sources that produced a concrete card/verifier
were admitted.

## Writing rules

- Keep `SKILL.md` short.
- Put details in `references/`.
- Add concrete bad signatures.
- Add a verifier for every rule.
- Add escape hatches to avoid cargo-cult behavior.
- Do not split into language-specific skills until forward tests prove it is
  necessary.
