# backend-craft bounded hook

`backend-craft-check.py` is a PostToolUse hook that runs cheap checkers on a
just-edited backend file (`.py`, `.go`, `.ts/.js`) and feeds at most **5**
findings back to the agent as additional context.

Contract (`../docs/CLAUDE_HANDOFF.md` task 4):

- project-local tools first: `uv run`/`poetry run` ruff, `go vet`,
  `pnpm exec`/`yarn exec`/`npx --no-install` eslint
- Semgrep `rules/semgrep/backend-craft.yml` as the gap-filler (changed file
  only; uses `semgrep` from PATH or `uvx semgrep`)
- max 5 findings per event, with an explicit "+N suppressed" notice
- session dedup: a finding (file:line:rule) surfaces once per session
- **always exits 0** — advisory only, never blocks a tool call, swallows its
  own failures (garbage stdin, missing tools, timeouts)
- one-time-per-session warning when no project-local checker exists for the
  file's language
- zero findings → zero output; the hook never says "safe". Every finding batch
  carries the disclaimer that a clean checker run is not backend safety
- skips `/fixtures/`, `/node_modules/`, `/.venv/`, `/vendor/` paths
  (declared-flawed corpora and dependencies)

## Wiring

Add to the target project's `.claude/settings.json` (or your user settings):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/backend-craft/hooks/backend-craft-check.py"
          }
        ]
      }
    ]
  }
}
```

Not wired into this repo's own settings on purpose: `fixtures/` is
intentionally flawed and the skill-development loop edits those files
constantly; the path skip covers it, but the hook belongs in consumer
projects, not here.

## Tests

```bash
hooks/test-hook.sh
```

7 scenarios, 14 assertions: findings + one-time warning, session dedup,
5-finding cap with suppression notice, non-backend silence, garbage-stdin
robustness, fixtures-path skip, go-vet-as-local-checker.

Session state lives in `$TMPDIR/backend-craft-hook/<sha(session_id)>.{seen,warned}`.
