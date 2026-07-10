#!/usr/bin/env python3
"""Deterministic TP/CLEAN check for the SQL-string-building rules.

Runs the pack over the probe files in this directory and compares the actual
findings against the inline annotations (works in both `.py` (`#`) and `.go`
(`//`) comment styles):

  ruleid: <full-rule-id>   the next code line MUST produce a finding for it
  ok: <full-rule-id>       the next code line MUST NOT produce a finding for it

Any finding on a line not covered by a matching `ruleid:` is a false positive.

Run from the repo root (semgrep must be available on PATH, or via uvx):
  python3 rules/semgrep/tests/check_probes.py

Exit 0 = expected == actual; 1 = mismatch (prints the diff matrix).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RULES = HERE.parent / "backend-craft.yml"
PROBES = sorted(p for p in HERE.iterdir() if p.suffix in {".py", ".go"})


def short(rid: str) -> str:
    return rid.rsplit(".", 1)[-1]


def semgrep_cmd() -> list[str]:
    if shutil.which("semgrep"):
        return ["semgrep"]
    if shutil.which("uvx"):
        return ["uvx", "semgrep"]
    print("ERROR: semgrep not found (need `semgrep` or `uvx` on PATH)")
    sys.exit(2)


def run_semgrep(path: pathlib.Path) -> set[tuple[int, str]]:
    out = subprocess.run(
        semgrep_cmd() + ["--config", str(RULES), "--no-git-ignore", "--metrics", "off", "--json", str(path)],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout)
    return {(r["start"]["line"], short(r["check_id"])) for r in data.get("results", [])}


def annotation(line: str) -> str | None:
    s = line.strip()
    for marker in ("#", "//"):
        if s.startswith(marker):
            return s[len(marker):].strip()
    return None


def expected(path: pathlib.Path) -> tuple[set[tuple[int, str]], set[tuple[int, str]]]:
    lines = path.read_text().splitlines()
    want, forbid = set(), set()
    for i, line in enumerate(lines):
        ann = annotation(line)
        if not ann:
            continue
        for tag, bucket in (("ruleid:", want), ("ok:", forbid)):
            if ann.startswith(tag):
                rid = short(ann[len(tag):].strip())
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or annotation(lines[j]) is not None):
                    j += 1
                if j < len(lines):
                    bucket.add((j + 1, rid))
    return want, forbid


def main() -> int:
    ok = True
    print(f"{'file':<30}{'line':>5}  {'kind':<11} rule                         result")
    for probe in PROBES:
        actual = run_semgrep(probe)
        want, forbid = expected(probe)
        for line, rid in sorted(want):
            hit = (line, rid) in actual
            ok = ok and hit
            print(f"{probe.name:<30}{line:>5}  {'TP':<11} {rid:<28} {'OK' if hit else 'MISSING <<<'}")
        for line, rid in sorted(forbid):
            hit = (line, rid) in actual
            ok = ok and not hit
            print(f"{probe.name:<30}{line:>5}  {'CLEAN':<11} {rid:<28} {'FALSE POSITIVE <<<' if hit else 'OK'}")
        for line, rid in sorted(actual):
            if (line, rid) not in want:
                ok = False
                print(f"{probe.name:<30}{line:>5}  {'UNEXPECTED':<11} {rid:<28} FALSE POSITIVE <<<")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
