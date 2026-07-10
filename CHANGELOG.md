# backend-craft evidence log

This is not a release changelog. It is the evidence log for rules that become
stronger over time.

Use [`FAILURE_CARDS.md`](FAILURE_CARDS.md) for the current card corpus.

## Entry format

```md
## YYYY-MM-DD - short-failure-name

Context:
Artifact:
Expected:
Why the agent likely failed:
Failure card:
Rule/reference changed:
Checker/test added:
Status: observed | production-tested | retired
```

## Promotion rule

- one plausible source-backed risk: `draft` in `FAILURE_CARDS.md`
- one real task failure: add entry here and mark card `observed`
- repeated failure or forward-test proof: mark card `production-tested`
- noisy or harmful rule: mark card `retired` and explain why

## Entries

## 2026-07-10 - forward-test-round-2

Context: 14 tests rerun on disposable fixture copies (grading markers and
READMEs stripped from copies — also closes a round-1 validity hole where
tested agents could see `PLANTED:` comments). Judges verified explicit
ROUND-2 FOCUS items for every round-1 miss. Originals verified untouched via
`git status`. Results in `forward-test-results/1xx-*.md`.
Artifact: `.claude/skills/backend-craft/`.
Expected: both round-1 3-scores close; no regressions.
Outcome: mean 3.93/4 (round 1: 3.86). 104 payment-idempotency 3->4 (agent
loaded persistence-migrations.md via the new payment/money routing signals,
discussed transaction boundary + outbox). 108 node-csv-export 3->4 (agent
loaded reliability-async.md via the new export signals, streamed with query-
level cap and concrete verifier). 13/14 round-1 misses closed.
Why the agent likely failed (the one regression): 114 rewrite-discipline 4->3
— wrote a 6-test regression file without loading testing-verification.md; the
Retrofit-mode sentence was not self-enforcing, and an SQL-injection fix loaded
only the security reference, not persistence-migrations.md.
Failure card: none new.
Rule/reference changed: SKILL.md testing row signals += "adding or writing any
new test file, regression tests for a fix"; SQL row += "fixing SQL injection /
parameterizing queries"; proof contract now requires testing-verification.md
in files-read when tests change; Continue mode mirrors the Retrofit testing
rule. From judge suggestions: api-contracts.md idempotency in-progress-key
lease/expiry rule + crash-retry verifier, export row cap enforced in the query
itself, language-adapters.md goroutine panic-recovery rule with sanctioned
stdlib fallback.
Checker/test added: none new (semantic).
Status: observed; `db-transaction-around-network-call` (104) and
`event-loop-blocking` (108) promoted to production-tested.

## 2026-07-10 - forward-test-round-1

Context: 14 blind forward tests (FORWARD_TESTS.md) run by fresh subagents
against the skill, scored by separate judges. Mean 3.86/4; twelve 4s, two 3s;
zero generic-advice answers. Full transcripts in `forward-test-results/`.
Artifact: `.claude/skills/backend-craft/` (SKILL.md + references).
Expected: every expected behavior in FORWARD_TESTS.md hit.
Why the agent likely failed (the misses):
- 004: task said "payment", never "transaction" — persistence-migrations.md
  never loaded, so transaction-around-network-call and outbox went unmentioned.
- 008: no routing signal for "export/bulk/streaming" — reliability-async.md not
  loaded; agent kept whole-CSV-in-memory with a "dataset is small" comment.
- 002: verify commands written as npm in a pnpm repo despite correct inventory.
- 009/010/014: single-row routing — second matching reference not loaded.
- 012: "log redaction test" satisfied by design comment, not a test.
Failure card: `db-transaction-around-network-call`, `event-loop-blocking`,
`api-idempotency-missing-on-mutation-retry` (safe pattern extended).
Rule/reference changed: SKILL.md routing table signals + load-all-matched-rows
rule + retrofit server-baseline/lockfile deliverables + proof-contract
re-verify clause; cross-links and prescriptive verifiers in
reliability-async.md, persistence-migrations.md, observability-ops.md,
api-contracts.md (exports-are-bounded-work), codebase-fit.md (lockfile rule).
Checker/test added: none new (misses are semantic, not mechanical).
Status: observed; 13 cards with direct forward-test proof promoted to
production-tested (test ids recorded in each card's Status line).

## 2026-07-10 - forward-test-isolation-incident

Context: same run. Implementation-shaped tasks ("add an endpoint...") made
tested agents edit the shared fixtures in place, mid-run: the BOLA plant was
"fixed", 20 new files appeared, sibling tests read mutated state.
Artifact: `fixtures/*`.
Expected: fixtures immutable during forward tests.
Why the agent likely failed: harness (this repo's process), not the tested
agents — prompts lacked a read-only/copy constraint and the repo has no VCS
snapshot.
Failure card: none (process failure).
Rule/reference changed: FORWARD_TESTS.md now has isolation rules: disposable
copy or design-only phrasing, do-not-read grading materials, restore +
re-verify after every run.
Checker/test added: post-restore acceptance = 3 fixture test suites green +
Semgrep hit set identical to the recorded baseline (9 hits; see CHECKERS.md).
Fixtures were restored from builder-transcript reconstruction and re-verified.
Status: observed

## 2026-07-10 - semgrep-floating-promise-rule-retired

Context: checker verification against a hand-built probe corpus (TP/CLEAN
labelled lines) before fixture testing.
Artifact: `rules/semgrep/backend-craft.yml` (old `ts.floating-promise-expression`).
Expected: flag only bare promise-valued call statements.
Why the rule failed: Semgrep matches subexpressions, so every awaited call
whose method name matched the prefix regex fired; measured precision ~1/8.
Statement anchoring (`$X;`, `$EXPR;` + metavariable-pattern) does not constrain
matching in the JS grammar. Name-prefix heuristics also missed real floating
calls (`auditLog.record`).
Failure card: `ts-floating-promise` (card kept; Semgrep verifier removed).
Rule/reference changed: rule deleted from the pack; `CHECKERS.md` documents the
delegation to type-aware `@typescript-eslint/no-floating-promises`.
Checker/test added: probe corpus kept the regression visible.
Status: retired (Semgrep rule only, not the card)

## 2026-07-10 - checker-pack-fixture-verification

Context: rule pack tested against probe corpus plus the three fixtures in
`fixtures/` (15 planted flaws total, 13 mechanically detectable by design).
Artifact: `rules/semgrep/backend-craft.yml`.
Expected: catch all mechanically detectable plants, zero false positives on
clean contrast code.
Why the agent likely failed: initial rules had arity/shape gaps — Python
`execute(f"...", params)` (two args) and adjacent f-string concatenation were
missed; constant f-strings were false positives; Go SQL-via-Sprintf had no rule
at all; Go goroutine/context rules fired on legitimate `main()` setup code.
Failure card: `sql-string-concat`, `go-goroutine-without-lifecycle`,
`timeout-without-cancellation-propagation`, `python-swallowed-exception`,
`api-mass-assignment`, `event-loop-blocking`.
Rule/reference changed: rules narrowed/added as recorded in `CHECKERS.md`
"Verification record (2026-07-10)"; all shipped rules now
`status: fixture-tested`.
Checker/test added: fixtures serve as the permanent regression corpus; rerun
command documented in `CHECKERS.md`.
Status: observed (checker-level evidence; cards unchanged pending forward tests)
