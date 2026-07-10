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
