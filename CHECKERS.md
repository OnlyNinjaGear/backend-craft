# backend-craft checkers

Checker rules are optional evidence. They should support failure cards, not
replace engineering review.

Current rule pack:

```text
rules/semgrep/backend-craft.yml
```

Run manually when Semgrep is available (no install needed with uv):

```bash
uvx semgrep --config rules/semgrep/backend-craft.yml --no-git-ignore --exclude node_modules .
```

A clean Semgrep run does not mean the backend is safe.

## Rule status ladder

- `draft`: written from a card, not yet tested against code
- `fixture-tested`: all planted true positives in `fixtures/` are caught and
  clean contrast code produces zero false positives (probe corpus + 3 fixtures)
- `production-tested`: also validated on at least one real backend
- removed: rule was noisier than the signal; the card keeps a non-Semgrep verifier

## Verification record (2026-07-10)

Tested against a hand-built probe corpus (TP/CLEAN-labelled lines per rule) and
the three fixture projects. Result: 13/13 mechanically detectable planted flaws
caught, 0 false positives on clean contrast code.

Scope note: the two Go server-timeout rules
(`go.listen-and-serve-no-timeouts`, `go.server-missing-read-timeouts`) were
added after this record and remain `draft` — probe-validated (TP + clean
variants) but with no fixture plant; the go-http fixture's correctly configured
server serves as their clean-pass regression only.

Narrowings made during verification:

- `python.sql-fstring-execute`: now requires an actual `{...}` interpolation
  (constant f-strings no longer flagged); matches two-arg
  `execute(f"...", params)` and adjacent f-string concatenation.
- `python.sql-format-or-concat-execute` (new): `%`, `.format()`, and `+`
  variants of SQL string building.
- `go.sql-sprintf-query` (new): `fmt.Sprintf` passed to
  `Query/QueryRow/Exec(+Context)` inline or via a local variable.
- `go.naked-goroutine-in-handler` and `go.context-background-in-handler`:
  scoped to functions with `(http.ResponseWriter, *http.Request)` signatures.
  Startup/`main()` uses are the cards' escape hatches and no longer fire.
  Worker/job paths are intentionally not covered; review those manually.
- `ts.mass-assignment-request-body`: dropped a speculative `{ ...req.body }`
  spread pattern (spreading a body is not by itself a persistence write).

Removed rule:

- `ts.floating-promise-expression`: Semgrep matches subexpressions, so every
  awaited call whose method name matched the prefix list fired (measured
  precision ~1/8 on the probe), while real floating calls with other names were
  missed. Statement anchoring (`$X;`, `$EXPR;`) does not constrain matching in
  the JS grammar. Floating promises need type information; the verifier for the
  `ts-floating-promise` card is `@typescript-eslint/no-floating-promises`
  (type-aware), not Semgrep. This is the "prefer project-local tools" rule in
  action.

Known intentional gaps (cards whose verifiers are not Semgrep):

- `go-ignored-error`: `errcheck` / `golangci-lint`
- `retry-without-jitter-or-cap`: no stable syntax signature; card verifier is a
  timing/count test
- `ts-floating-promise`, `ts-any-at-boundary`: typescript-eslint + `tsc`
- `api-bola-id-swap`, `api-idempotency-missing-on-mutation-retry`,
  `db-transaction-around-network-call`: semantic; covered by skill review and
  the fixtures' forward tests

## Real-backend validation record (2026-07-10, henry monorepo)

Read-only run over `~/Documents/VSCode/henry` (NestJS admin API, Go Temporal
workers, Python workers; 361 backend source files): **49 findings, 0 parse
errors, 0 wrong-match false positives** (every hit is the exact syntactic
pattern; contextual severity varies exactly as the rule messages hedge).

- `node.sync-fs-in-code` (48 hits): sample-verified. `settings.controller.ts`
  — `readFileSync`/`writeFileSync` inside a `@Put` HTTP handler (true
  positive); `devops.service.ts` — `existsSync` in admin restart endpoints
  (true-by-signature, low severity in context — validates WARNING as the right
  level). Promoted to `production-tested`.
- `python.swallowed-exception-pass` (1 hit): `gemini.py` `except Exception:
  pass # skip unloadable images` — documented best-effort skip; the card's
  escape hatch requires comment + metric, only the comment exists, so the
  advisory stands. Promoted to `production-tested`.
- All other rules: zero hits. FN-probe greps confirmed the repo genuinely has
  no target constructs (no raw SQL string building — Drizzle ORM; no
  `http.ListenAndServe` — Temporal workers, not HTTP servers; the single
  `go func` is outside handler scope by design). True negatives, statuses
  unchanged.

Hook validation on the same repo (synthetic PostToolUse events on real files):
findings + dedup + exit 0 across TS/Python/Go; ~1.3-1.8s per event with
Semgrep, first Go event ~8s (cold `go vet` build; warm cache is fast). Found
and fixed a monorepo bug: eslint deps and lockfile live at the workspace root,
not the nearest `package.json` — detection now walks up to the lockfile root.
Henry's eslint is declared but not installed, so the no-local-checker warning
fired correctly.

## Rule admission bar

Each checker must map to a failure card:

- `metadata.failure_card`
- concrete message with blast radius
- source reference when applicable
- clear escape hatch in the message or card

Prefer existing project-local tools first:

- Python: Ruff, mypy, pytest
- Go: `go test`, `go vet`, golangci-lint (`errcheck`)
- TS/Node: project-local typecheck/eslint/test
  (`@typescript-eslint/no-floating-promises` requires type-aware linting)
- API: OpenAPI validation/diff, Pact where present
- DB: migration dry run, query plan, query count tests

Use Semgrep/ast-grep for gaps the local toolchain does not cover. Do not write
noisy regex-only detectors unless the signature is extremely stable.

## Bounded hook

`hooks/backend-craft-check.py` packages the pack as a PostToolUse hook:
project-local tools first, Semgrep gap-filler on the changed file, max 5
findings, session dedup, always exit 0, one-time no-local-checker warning,
never claims safety. Wiring and test suite: `hooks/README.md`,
`hooks/test-hook.sh` (14 assertions).
