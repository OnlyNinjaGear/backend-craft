# backend-craft fixtures

Small, runnable, **intentionally flawed** backend projects. They exist to:

1. forward-test the `backend-craft` skill (does an agent using the skill catch
   the planted failures without being told about them?)
2. regression-test the checker pack in `rules/semgrep/backend-craft.yml`
   (every mechanically detectable plant must be caught; clean contrast code
   must produce zero false positives)

Each fixture has its own README with the exact test command and a table of
planted failures mapped to `../FAILURE_CARDS.md` card ids. Plants are marked in
code with `PLANTED: <card-id>` comments. Counting convention: a "plant" is one
planted failure — one failure may span several marked sites (go-http's
server-timeout plant has two) and one marked line may cite two card ids
(python's dual-mapped plants), so marker-site count ≠ plant count.

| fixture | stack | test command | plants |
|---|---|---|---|
| `python-fastapi/` | FastAPI + stdlib sqlite3, uv | `uv run pytest -q` | 5 |
| `go-http/` | Go stdlib net/http, zero deps | `go vet ./... && go test ./...` | 6 |
| `ts-fastify/` | Fastify + TypeScript + vitest, pnpm | `pnpm install && pnpm test` | 5 |

Pristine baseline: `pristine-baseline-20260710.tar.gz` (sources only, no
node_modules/.venv; regenerated 2026-07-10 after the go-http server-timeout
plant landed). Restore from it and re-run the acceptance pass below if a
forward-test run ever mutates the fixtures again. Expected Semgrep baseline:
11 hits (5 in `go-http/`, 3 each in the others; see each README for the
intentionally non-Semgrep cards).

Rules:

- Do not fix the planted flaws. The fixtures exist to be reviewed, not repaired.
- Happy-path tests must stay green; flaws are production-safety flaws, not
  compile errors.
- When forward-testing an agent against a fixture, do not let it read the
  fixture's README.md or the repo-root grading docs — they list the answers.
- Checker acceptance: run
  `uvx semgrep --config ../rules/semgrep/backend-craft.yml --no-git-ignore --exclude node_modules .`
  from this directory and compare hits against each README's table
  (see `../CHECKERS.md` for which cards are intentionally not Semgrep-covered).
