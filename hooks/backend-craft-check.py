#!/usr/bin/env python3
"""backend-craft bounded PostToolUse hook.

Runs cheap checkers on a just-edited backend file and surfaces at most
MAX_FINDINGS findings to the agent as additional context. Design rules
(see CLAUDE_HANDOFF.md task 4 and CHECKERS.md):

- project-local tools first (uv/poetry run ruff, go vet, pnpm/yarn/npx eslint)
- Semgrep backend-craft pack as the gap-filler, changed file only
- max 5 findings per event
- dedup within a session: a finding shown once is never repeated
- ALWAYS exit 0; never blocks, never fails the tool call
- one-time-per-session warning when no project-local checker exists
- never claims safety: zero findings -> zero output (a clean run is silence,
  not "backend safe")

Wire-up (see hooks/README.md): PostToolUse hook matching Edit|Write|MultiEdit.
Input: hook JSON on stdin. Output: PostToolUse additionalContext JSON.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

MAX_FINDINGS = 5
TOOL_TIMEOUT_S = 20
PACK_DIR = os.path.dirname(os.path.abspath(__file__))
SEMGREP_RULES = os.path.join(PACK_DIR, "..", "rules", "semgrep", "backend-craft.yml")

BACKEND_EXTS = {".py", ".go", ".ts", ".tsx", ".js", ".mjs", ".cjs"}


def out(payload: dict) -> None:
    print(json.dumps(payload))
    sys.exit(0)


def silent_exit() -> None:
    sys.exit(0)


def run(cmd, cwd=None):
    try:
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_S
        )
        return p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, OSError):
        return None, "", ""


def find_up(start_dir, names):
    d = start_dir
    while True:
        for n in names:
            if os.path.exists(os.path.join(d, n)):
                return d, n
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def state_paths(session_id: str):
    base = os.path.join(tempfile.gettempdir(), "backend-craft-hook")
    os.makedirs(base, exist_ok=True)
    sid = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return (
        os.path.join(base, f"{sid}.seen"),
        os.path.join(base, f"{sid}.warned"),
    )


def load_lines(path):
    try:
        with open(path) as f:
            return set(line.strip() for line in f if line.strip())
    except OSError:
        return set()


def append_lines(path, lines):
    try:
        with open(path, "a") as f:
            for line in lines:
                f.write(line + "\n")
    except OSError:
        pass


# --- checkers ---------------------------------------------------------------
# Each returns (findings, had_project_local_checker).
# A finding is (dedup_key, display_line).


def check_python(file_path, project_dir):
    findings, local = [], False
    runner = None
    if project_dir:
        if os.path.exists(os.path.join(project_dir, "uv.lock")) and shutil.which("uv"):
            runner = ["uv", "run", "--no-sync", "ruff"]
        elif os.path.exists(os.path.join(project_dir, "poetry.lock")) and shutil.which("poetry"):
            runner = ["poetry", "run", "ruff"]
    if runner:
        rc, stdout, _ = run(runner + ["check", "--output-format", "concise", file_path], cwd=project_dir)
        if rc is not None and rc in (0, 1):
            local = True
            for line in stdout.splitlines():
                if line.strip() and ":" in line:
                    findings.append((line.strip(), f"[ruff] {line.strip()}"))
    return findings, local


def check_go(file_path, project_dir):
    findings, local = [], False
    if project_dir and shutil.which("go"):
        rel_pkg = "./" + os.path.relpath(os.path.dirname(file_path), project_dir)
        rc, _, stderr = run(["go", "vet", rel_pkg], cwd=project_dir)
        if rc is not None:
            local = True
            for line in stderr.splitlines():
                line = line.strip()
                if line and ":" in line and not line.startswith("#"):
                    findings.append((line, f"[go vet] {line}"))
    return findings, local


def check_ts(file_path, project_dir):
    findings, local = [], False
    if not project_dir:
        return findings, local
    pkg_json = os.path.join(project_dir, "package.json")
    has_eslint = False
    try:
        with open(pkg_json) as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        has_eslint = "eslint" in deps
    except (OSError, json.JSONDecodeError):
        pass
    if not has_eslint:
        return findings, local
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")) and shutil.which("pnpm"):
        runner = ["pnpm", "exec", "eslint"]
    elif os.path.exists(os.path.join(project_dir, "yarn.lock")) and shutil.which("yarn"):
        runner = ["yarn", "exec", "eslint"]
    elif shutil.which("npx"):
        runner = ["npx", "--no-install", "eslint"]
    else:
        return findings, local
    rc, stdout, _ = run(runner + ["--format", "unix", file_path], cwd=project_dir)
    if rc is not None and rc in (0, 1):
        local = True
        for line in stdout.splitlines():
            line = line.strip()
            if line and ":" in line and line[0] == os.sep:
                findings.append((line, f"[eslint] {line}"))
    return findings, local


def check_semgrep(file_path):
    """Gap-filler: backend-craft pack on the changed file only."""
    findings = []
    rules = os.path.normpath(SEMGREP_RULES)
    if not os.path.exists(rules):
        return findings
    if shutil.which("semgrep"):
        cmd = ["semgrep"]
    elif shutil.which("uvx"):
        cmd = ["uvx", "semgrep"]
    else:
        return findings
    rc, stdout, _ = run(
        cmd + ["--config", rules, "--no-git-ignore", "--quiet", "--json",
               "--metrics", "off", "--disable-version-check", file_path]
    )
    if rc is None or not stdout:
        return findings
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return findings
    for r in data.get("results", []):
        rule = r.get("check_id", "").split(".")[-1]
        line = r.get("start", {}).get("line", 0)
        msg = (r.get("extra", {}).get("message", "") or "").split(". ")[0]
        card = r.get("extra", {}).get("metadata", {}).get("failure_card", "")
        key = f"{r.get('path','')}:{line}:{rule}"
        display = f"[semgrep:{rule}] {r.get('path','')}:{line} {msg}"
        if card:
            display += f" (card: {card})"
        findings.append((key, display))
    return findings


# --- main -------------------------------------------------------------------


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        silent_exit()

    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    session_id = event.get("session_id") or "no-session"

    ext = os.path.splitext(file_path)[1]
    if ext not in BACKEND_EXTS or not os.path.isfile(file_path):
        silent_exit()
    # never lint declared-flawed fixture corpora or dependency dirs
    norm = file_path.replace(os.sep, "/")
    if any(seg in norm for seg in ("/node_modules/", "/.venv/", "/vendor/", "/fixtures/")):
        silent_exit()

    seen_path, warned_path = state_paths(session_id)
    seen = load_lines(seen_path)
    warned = load_lines(warned_path)

    start_dir = os.path.dirname(os.path.abspath(file_path))
    if ext == ".py":
        project_dir, _ = find_up(start_dir, ["pyproject.toml", "setup.cfg", "requirements.txt"])
        findings, local = check_python(file_path, project_dir)
        lang = "python"
    elif ext == ".go":
        project_dir, _ = find_up(start_dir, ["go.mod"])
        findings, local = check_go(file_path, project_dir)
        lang = "go"
    else:
        project_dir, _ = find_up(start_dir, ["package.json"])
        findings, local = check_ts(file_path, project_dir)
        lang = "ts"

    findings += check_semgrep(file_path)

    messages = []

    if not local and lang not in warned:
        append_lines(warned_path, [lang])
        messages.append(
            f"backend-craft: no project-local {lang} checker found for this file "
            "(looked for uv/poetry+ruff, go vet, or a project eslint). Only the "
            "Semgrep gap-filler ran. Consider wiring the project's own linter; "
            "this warning shows once per session."
        )

    fresh = [(k, d) for k, d in findings if k not in seen]
    if fresh:
        shown = fresh[:MAX_FINDINGS]
        append_lines(seen_path, [k for k, _ in shown])
        lines = [d for _, d in shown]
        suffix = ""
        dropped = len(fresh) - len(shown)
        if dropped > 0:
            suffix = f"\n(+{dropped} more findings suppressed by the {MAX_FINDINGS}-finding cap; run the checkers directly for the full list)"
        messages.append(
            "backend-craft checkers on the file you just edited "
            "(advisory only; a clean checker run is NOT evidence the backend is safe):\n"
            + "\n".join(lines)
            + suffix
        )

    if not messages:
        silent_exit()

    out({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n\n".join(messages),
        }
    })


if __name__ == "__main__":
    main()
