# backend-craft evidence log

This is not a release changelog. It is the evidence log for rules that become
stronger over time.

Use [`FAILURE_CARDS.md`](../FAILURE_CARDS.md) for the current card corpus.

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

- one plausible source-backed risk: `draft` in `../FAILURE_CARDS.md`
- one real task failure: add entry here and mark card `observed`
- repeated failure or forward-test proof: mark card `production-tested`
- noisy or harmful rule: mark card `retired` and explain why

## Entries

## 2026-07-19 - drf-default-permission-unset-card-added

Context: daily case-triage run over the intake queue (issues #2-#7, all
Django/DRF authorization findings from one anonymized case source). Picked
issue #4 as the single most promising candidate: it is the root-cause failure
mode several of the sibling issues build on top of, it does not duplicate any
existing card (`authz-handler-only` and `auth-middleware-scope-miss` are about
encapsulation/scope, not the framework's own permission default), and Django +
DRF are actually installed in this environment (Django 6.0.7,
djangorestframework 3.17.1) so the reducer runs against the real library
instead of a mock.
Artifact: `../FAILURE_CARDS.md` (new card `drf-default-permission-unset`),
`tests/cards/drf_permission_fail_open.py` (new reducer),
`tests/cards/test_drf_permission_fail_open.py` (new verifier).
Expected: a view with no `permission_classes` should deny an unauthenticated,
zero-credential request.
Why the agent likely failed: `REST_FRAMEWORK` sets
`DEFAULT_AUTHENTICATION_CLASSES` (so it looks like auth is "handled") but
never sets `DEFAULT_PERMISSION_CLASSES`; confirmed against the installed
`rest_framework.settings.DEFAULTS` that DRF's own shipped default for that key
is `AllowAny`. A view that forgets `permission_classes` is not a 500, it is
silently public. Reducer runs the same `APIView` in two subprocesses (Django
settings can only be configured once per process, and
`APIView.permission_classes` binds to `api_settings.DEFAULT_PERMISSION_CLASSES`
at `rest_framework.views` import time) -- one with the setting unset (200 to
zero credentials), one with `DEFAULT_PERMISSION_CLASSES` set to
`IsAuthenticated` (403 to the same request).
Failure card: `drf-default-permission-unset` (draft -- source-backed and now
fixture-tested via a real installed Django/DRF reducer; not yet observed
against a second independent real project or forward-tested).
Rule/reference changed: card added; no existing card or reference edited.
Checker/test added: `python -m pytest tests/cards/test_drf_permission_fail_open.py -q`
-- 2 passed (unset -> 200, fixed -> 403); full suite
`python -m pytest tests/cards/ -q` -> 4 passed, 1 skipped (skip is the
pre-existing PostgreSQL card with no reachable DB in this environment,
unrelated to this change).
Status: draft (card-level; fixture-tested reducer proves the mechanism, no
forward test or second real-project sighting yet)

## 2026-07-10 - coverage-and-cards-fix-pass-after-hostile-review

Context: `backend-craft/coverage-and-cards` branch. An adversarial Codex review
of an earlier version of this branch found the new material was overclaimed:
the two new Semgrep SQL rules matched ANY `text(...)`/`Sprintf(...)`, two cards
were promoted to `observed` without a defensible in-folder occurrence, and doc
counts drifted. This pass narrows the rules to something precise, keeps every
new card and rule at `draft`, and adds runnable proof for each card.
Artifact: `rules/semgrep/backend-craft.yml` (3 new rules, all `draft`),
`rules/semgrep/tests/` (probe corpus + `check_probes.py`), `tests/cards/`
(gather + PostgreSQL reducers and tests), `FAILURE_CARDS.md` (2 new cards),
`README.md`, `README.en.md`, `docs/STATUS.md`, `scripts/validate_repo.py`,
`hooks/README.md`.
Expected: rules fire on the real SQL-building shape and stay silent on the safe
shape (proven by a persistent probe matrix, not a claim); each new card carries
a reducer that actually reproduces the failure; no status inflated on evidence
that cannot be checked from inside this folder.
Why the agent likely failed (the two new cards' failure modes):
- `python-gather-partial-failure-leak`: an agent reads `asyncio.gather` as an
  atomic batch — assumes a raise cancels the siblings and leaves no partial
  writes. Neither holds; even `TaskGroup` (which does cancel) cannot roll back a
  side effect committed before the cancel point.
- `pg-non-atomic-poll-queue-claim`: an agent claims a job with `SELECT ...
  pending` then a separate `UPDATE ... running` with no lock/guard; two workers
  read the same row and both process it. The defect is the non-atomic claim, not
  "missing SKIP LOCKED" specifically.
Failure card: `python-gather-partial-failure-leak` (new, draft),
`pg-non-atomic-poll-queue-claim` (new, draft); the 3 new rules map to the
existing `sql-string-concat` card (unchanged).
Rule/reference changed: the 3 new rules are scoped so they only match the real
sink — the Python rules rely on Semgrep import resolution to match
`sqlalchemy.text(...)` (a local `text()`/`ui.text()` is not matched); the Go
rule matches `fmt.Sprintf` passed INLINE to a pgx `Query/QueryRow/Exec(ctx,...)`
only (a pre-built string is a documented FN, not a false "clean"). No existing
rule or card logic was changed.
Checker/test added: `rules/semgrep/tests/check_probes.py` (deterministic TP/CLEAN
matrix over `sql_text_sqlalchemy.py`, `sql_text_not_sqlalchemy.py`, `go_pgx.go`;
`python3 rules/semgrep/tests/check_probes.py` → PASS); `tests/cards/
gather_partial_failure.py` + `test_gather_partial_failure.py`; `tests/cards/
pg_non_atomic_claim.py` + `test_pg_non_atomic_claim.py` (PostgreSQL; 4 tests).
Decisions on the two earlier promotions (both reverted to card status on main):
- `secret-in-config-or-log`: NOT promoted. Establishing "observed" needs proof
  the file was tracked and not a fixture/example/deterministic-fake key, and the
  only candidate is a private key I was instructed not to read/verify. Insufficient
  in-folder evidence → stays `draft`.
- `python-swallowed-exception`: NOT promoted. The real occurrence is already the
  henry real-backend record below (the checker rule `python.swallowed-exception-pass`
  is production-tested there); adding a new "first occurrence" entry would
  contradict it. Card stays `draft`; no new claim invented.
Status: draft. No card or rule was promoted in this pass.

## 2026-07-10 - codex-re-review-round-2

Context: external Codex re-review of commits f2e346e/afa85c5 plus fresh
artifacts. Five findings, all verified and fixed.
Artifact: `forward-test-results/0*.md`, `hooks/backend-craft-check.py`,
`../hooks/test-hook.sh`, status docs, `../FAILURE_CARDS.md`.
Expected: previous remediation complete; hook contract airtight.
Why the agent likely failed (per finding):
1. P1 confirmed — round-1 result files 001-014 still had empty Prompt blocks
   (previous fix only covered 1xx). Filled from the round-1 script.
2. P1 confirmed — hook crashed (exit 1) when no writable temp dir exists:
   `state_paths()` was unguarded. Fixed: probe-write with fallback to
   stateless mode (dedup degrades, findings still emitted), plus a global
   catch-all exit-0 backstop; `test-hook.sh` now fails fast when `mktemp`
   itself is broken. Verified: hostile `TMPDIR` -> rc=0 with findings.
3. P2 confirmed — docs said "pack fixture-tested" while the two later-added
   Go server-timeout rules are `draft`. Scope note added to CHECKERS/README/
   HANDOFF instead of overclaiming.
4. P2 confirmed — `go-goroutine-without-lifecycle` safe pattern named errgroup
   without panic capture. Card now requires in-goroutine defer/recover and
   cites the x/sync no-panic-propagation design (verified v0.22.0 source).
5. P3 confirmed — no-local-checker warning claimed "Only the Semgrep
   gap-filler ran" even when Semgrep was unavailable. `check_semgrep` now
   reports whether it actually ran; the warning states "NOTHING checked this
   edit" when true.
Status: observed

## 2026-07-10 - real-backend-validation-henry

Context: pack + hook run read-only against the henry monorepo (NestJS admin
API, Go Temporal workers, Python workers). Full record in `CHECKERS.md`
"Real-backend validation record".
Outcome: 49 findings, 0 parse errors, 0 wrong-match FPs; sample-verified TPs
(sync fs in a @Put handler; documented-but-unmetered swallowed exception).
`node.sync-fs-in-code` and `python.swallowed-exception-pass` promoted to
production-tested. FN-probes confirmed silent rules are true negatives.
Hook: found and fixed the monorepo eslint/lockfile-at-workspace-root detection
bug; latency ~1.3-1.8s (Semgrep), ~8s cold go vet.
Status: observed

## 2026-07-10 - forward-test-round-3

Context: targeted regression round for the round-2 miss (test-writing without
`testing-verification.md`). Two 114-style tasks on fresh leak-stripped copies:
301 "write tests for search + user update", 302 exact rerun of the NestJS
rewrite question. Results in `forward-test-results/30x-*.md`.
Artifact: `.claude/skills/backend-craft/SKILL.md`.
Expected: the round-2 fixes (testing routing signals + proof-contract gate)
fire; no recurrence.
Outcome: both 4/4, both regression_closed. 302 clean sweep — zero misses:
testing-verification.md loaded for the 5 new regression tests AND
persistence-migrations.md fired via the new "fixing SQL injection" signal.
301 passed all FOCUS items (differential pre-fix test run proving the tests
catch the planted bugs; judge reproduced 27/27 + clean typecheck) but exposed
the same gap-class on a different path: persistence-migrations.md not loaded
when the SQL fix emerged mid-task, i.e. after the initial Impact Read chose
references.
Failure card: none new.
Rule/reference changed: SKILL.md — proof contract gains a SQL hard gate
(mirror of the testing gate), and the routing section now requires a
pre-report re-scan of the actual diff against the table (closes the
class: rows that start matching mid-task).
Checker/test added: none (semantic).
Status: observed. Hard gates demonstrably work where routing-table matching
alone does not (302 proved the round-2 gates; 301's miss was on the one row
without a gate at the time).

## 2026-07-10 - errgroup-panic-claim-corrected

Context: round-2 judge (test 109) asserted errgroup >= v0.9.0 re-panics on the
waiting goroutine; the claim entered `language-adapters.md`. External review
(Codex) flagged it for verification.
Artifact: `references/language-adapters.md` Goroutines section.
Expected: library claims verified against source before entering references.
Why it was wrong: x/sync v0.22.0 `errgroup.go` contains an explicit design
comment REJECTING panic propagation (delays panics, hides stacks from crash
tooling, deadlock risk; issues #53757, #74275, #74304, #74306). Verified in
the module source, not from memory.
Rule/reference changed: section rewritten — errgroup does NOT propagate
panics; goroutines that may panic need their own defer/recover.
Lesson recorded: judge-suggested edits that assert library behavior go through
the same official-docs/source gate as any dependency guidance.
Status: observed

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

Context: 14 blind forward tests (`FORWARD_TESTS.md`) run by fresh subagents
against the skill, scored by separate judges. Mean 3.86/4; twelve 4s, two 3s;
zero generic-advice answers. Full transcripts in `forward-test-results/`.
Artifact: `.claude/skills/backend-craft/` (SKILL.md + references).
Expected: every expected behavior in `FORWARD_TESTS.md` hit.
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
Rule/reference changed: `FORWARD_TESTS.md` now has isolation rules: disposable
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

## 2026-07-10 - go-server-timeout-rules-promoted-to-fixture-tested

Context: the two Go server-timeout rules (`go.listen-and-serve-no-timeouts`,
`go.server-missing-read-timeouts`) were probe-validated `draft` with no
fixture plant; closing the last non-fixture-tested gap in the shipped pack.
Artifact: `fixtures/go-http/ops.go` (new), `fixtures/go-http/main.go`,
`rules/semgrep/backend-craft.yml`, `CHECKERS.md`, fixture READMEs,
regenerated `fixtures/pristine-baseline-20260710.tar.gz`.
Expected: both rules catch a realistic plant and stay silent on the fixture's
correctly configured server.
Why the agent likely failed (the card's failure mode): ops/debug listeners are
the classic spot — a bare `&http.Server{Addr, Handler}` ops endpoint and the
canonical-looking `http.ListenAndServe(":6060", nil)` debug listener, both on
all interfaces (the docs' own example uses `localhost:6060`; dropping the host
silently widens exposure with zero timeouts).
Failure card: `go-http-server-no-timeouts` (card itself stays `draft` on the
card ladder — planted, not yet observed in a real project or forward test).
Rule/reference changed: both rules `draft` -> `fixture-tested`; promotion
record in `CHECKERS.md`; go-http plant count 5 -> 6 (16 total across
fixtures); expected Semgrep baseline 9 -> 11 hits.
Checker/test added: fixture plants are the permanent regression; probe corpus
rerun 4/4 TP, 0 FP on clean variants (ReadHeaderTimeout-only,
ReadTimeout-only, method-call ListenAndServe, httptest); `go vet` + happy-path
tests green; the new `go startOps()`/`go startDebug()` in `main()` double as
a no-fire scoping regression for `go.naked-goroutine-in-handler`.
Status: observed (checker-level evidence)

## 2026-07-10 - auth-middleware-scope-miss-card-added

Context: handoff item "framework-specific auth docs for the fixture stacks";
admission bar = concrete card/verifier only, no generic advice.
Artifact: `../FAILURE_CARDS.md` (new card), `SOURCES.md` (3 rows),
`references/auth-tenancy-security.md` (non-negotiable + verifier line).
Expected: auth guards cover every non-public route.
Why the agent likely fails: registers the auth guard on a sub-scope assuming
it is global — Fastify hooks are encapsulated per plugin context (siblings
unaffected), FastAPI router-level dependencies "only affect that APIRouter",
a wrapped Go sub-mux covers only what it wraps; a route module added outside
the guarded scope ships unauthenticated and nothing errors.
Failure card: `auth-middleware-scope-miss` (draft — source-backed, not yet
observed in a project or forward test).
Rule/reference changed: card added; auth reference gained "Auth guards attach
at the shared ancestor scope" and the route-table sweep verifier.
Checker/test added: none mechanical (scope topology is semantic); verifier is
the unauthenticated route-table sweep (all non-allowlisted routes 401/403).
Sources verified against fastify.dev and fastapi.tiangolo.com on 2026-07-10.
Status: draft (card-level; no fixture plant — fixtures use fake header auth
by design, zero-dep philosophy)
