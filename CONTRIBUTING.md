# Contributing

`backend-craft` v0.1 is frozen. Please do not expand scope by default.

Acceptable changes:

- bug fixes in existing instructions, checkers, fixtures, or hook behavior
- documentation fixes
- CI or packaging fixes
- new evidence for an existing failure card

New domains, languages, libraries, or rule families require an explicit owner
decision before implementation.

## Rule Admission Bar

New backend knowledge must produce at least one of:

- a failure card
- a verifier
- a checker
- a source-backed playbook step

Avoid generic advice such as "write secure code" or "handle errors well".

## Validation

Run before submitting changes:

```bash
python3 -m pip install pyyaml
python3 scripts/validate_repo.py
hooks/test-hook.sh
```

Run fixture-specific commands when changing fixtures or rules:

```bash
cd fixtures/python-fastapi && uv run pytest -q
cd ../go-http && go vet ./... && go test ./...
cd ../ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test
```
