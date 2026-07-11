#!/usr/bin/env python3
"""Repository sanity checks for backend-craft.

This is packaging/CI glue only. It validates that the public repo shape still
matches the frozen v0.1 artifacts without changing skill behavior.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "backend-craft" / "SKILL.md"
RULES = ROOT / "rules" / "semgrep" / "backend-craft.yml"
CARDS = ROOT / "FAILURE_CARDS.md"


def fail(message: str) -> None:
    print(f"validate_repo: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")


def validate_skill() -> None:
    text = read(SKILL)
    if not text.startswith("---\n"):
        fail("SKILL.md is missing YAML frontmatter")
    try:
        frontmatter = text.split("---\n", 2)[1]
        data = yaml.safe_load(frontmatter)
    except Exception as exc:  # noqa: BLE001 - this is a validation script
        fail(f"SKILL.md frontmatter is invalid YAML: {exc}")
    if data.get("name") != "backend-craft":
        fail("SKILL.md frontmatter name must be backend-craft")
    if "backend" not in str(data.get("description", "")).lower():
        fail("SKILL.md description no longer triggers on backend work")

    missing_refs: list[str] = []
    for ref in sorted(set(re.findall(r"`(references/[^`]+\.md)`", text))):
        if not (SKILL.parent / ref).exists():
            missing_refs.append(ref)
    if missing_refs:
        fail("SKILL.md references missing files: " + ", ".join(missing_refs))


def validate_rules() -> None:
    try:
        rules_doc = yaml.safe_load(read(RULES))
    except Exception as exc:  # noqa: BLE001
        fail(f"Semgrep rule pack is invalid YAML: {exc}")
    rules = rules_doc.get("rules")
    if not isinstance(rules, list) or not rules:
        fail("Semgrep rule pack has no rules")

    card_ids = set(re.findall(r"^## ([a-z0-9-]+)$", read(CARDS), re.MULTILINE))
    missing_cards: list[str] = []
    missing_status: list[str] = []
    for rule in rules:
        metadata = rule.get("metadata") or {}
        card = metadata.get("failure_card")
        if card not in card_ids:
            missing_cards.append(f"{rule.get('id')} -> {card}")
        if "status" not in metadata:
            missing_status.append(str(rule.get("id")))
    if missing_cards:
        fail("Semgrep rules reference missing failure cards: " + ", ".join(missing_cards))
    if missing_status:
        fail("Semgrep rules missing metadata.status: " + ", ".join(missing_status))


def validate_fixtures() -> None:
    fixtures_readme = read(ROOT / "fixtures" / "README.md")
    plant_counts = [int(value) for value in re.findall(r"\|\s*`[^`]+/`\s*\|[^|]+\|[^|]+\|\s*(\d+)\s*\|", fixtures_readme)]
    expected_plants = sum(plant_counts)
    if expected_plants != 16:
        fail(f"fixtures/README.md should document 16 planted flaws, found {expected_plants}")

    markers = []
    for path in (ROOT / "fixtures").glob("**/*"):
        if path.is_file() and path.suffix in {".py", ".go", ".ts"}:
            markers.extend(re.findall(r"PLANTED:", read(path)))
    if len(markers) < expected_plants:
        fail(f"expected at least {expected_plants} PLANTED markers in fixtures, found {len(markers)}")


def validate_forward_results() -> None:
    for path in sorted((ROOT / "forward-test-results").glob("*.md")):
        text = read(path)
        if "Score:" not in text:
            fail(f"{path.relative_to(ROOT)} has no Score line")
        match = re.search(r"## Prompt\n\n```text\n(?P<prompt>.*?)\n```", text, re.DOTALL)
        if not match or not match.group("prompt").strip():
            fail(f"{path.relative_to(ROOT)} has an empty Prompt block")


def validate_markdown_links() -> None:
    for path in sorted(ROOT.glob("**/*.md")):
        if any(part in {".git", "_reference", "node_modules", ".venv"} for part in path.parts):
            continue
        text = read(path)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if (
                "://" in target
                or target.startswith("#")
                or target.startswith("mailto:")
                or target.startswith("app://")
            ):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                fail(f"{path.relative_to(ROOT)} links to missing path: {target}")


def _rule_counts() -> tuple[int, dict[str, int]]:
    rules = (yaml.safe_load(read(RULES)) or {}).get("rules") or []
    by_status: dict[str, int] = {}
    for rule in rules:
        status = (rule.get("metadata") or {}).get("status")
        by_status[status] = by_status.get(status, 0) + 1
    return len(rules), by_status


def _card_counts() -> tuple[int, dict[str, int]]:
    text = read(CARDS)
    ids = re.findall(r"^## ([a-z0-9-]+)$", text, re.MULTILINE)
    # 'card-id' is the placeholder header inside the "Card template" section.
    card_ids = [cid for cid in ids if cid != "card-id"]
    by_status: dict[str, int] = {}
    for status in re.findall(r"^Status: ([a-z-]+)", text, re.MULTILINE):
        by_status[status] = by_status.get(status, 0) + 1
    return len(card_ids), by_status


def validate_doc_counts() -> None:
    """Fail if any human-facing doc disagrees with the real rule/card counts.

    Truth is computed from the Semgrep pack and FAILURE_CARDS.md. README.md,
    README.en.md and docs/STATUS.md must all quote the same numbers, so a rule
    or card added without a doc update is a build failure, not a silent drift.
    """
    n_rules, by_status = _rule_counts()
    n_cards, card_statuses = _card_counts()
    n_draft = by_status.get("draft", 0)
    n_fixture = by_status.get("fixture-tested", 0)
    n_production = by_status.get("production-tested", 0)
    n_card_draft = card_statuses.get("draft", 0)
    n_card_production = card_statuses.get("production-tested", 0)

    readme = ROOT / "README.md"
    readme_en = ROOT / "README.en.md"
    status = ROOT / "docs" / "STATUS.md"

    # (path, human label, regex capturing the claimed number, truth)
    checks: list[tuple[pathlib.Path, str, str, int]] = [
        (readme, "README badge rule count", r"semgrep-(\d+)%20rules", n_rules),
        (readme, "README 'Semgrep rules' row", r"\|\s*Semgrep rules\s*\|\s*(\d+)\s*\|", n_rules),
        (readme, "README 'Failure cards' row", r"\|\s*Failure cards\s*\|\s*(\d+)\s*\|", n_cards),
        (readme, "README production card row", r"\|\s*Карточки со статусом `production-tested`\s*\|\s*(\d+)\s*\|", n_card_production),
        (readme, "README 'draft' rules row", r"\|\s*Rules со статусом `draft`\s*\|\s*(\d+)\s*\|", n_draft),
        (readme_en, "README.en cards", r"(\d+)\s+failure cards", n_cards),
        (readme_en, "README.en rules", r"(\d+)\s+Semgrep rules", n_rules),
        (readme_en, "README.en production cards", r"including\s+(\d+)\s+`production-tested` cards", n_card_production),
        (status, "STATUS cards", r"\|\s*Failure cards\s*\|\s*(\d+)\s*\|", n_cards),
        (status, "STATUS production cards", r"\|\s*Cards со статусом `production-tested`\s*\|\s*(\d+)\s*\|", n_card_production),
        (status, "STATUS draft cards", r"\|\s*Cards со статусом `draft`\s*\|\s*(\d+)\s*\|", n_card_draft),
        (status, "STATUS rules", r"\|\s*Semgrep rules\s*\|\s*(\d+)\s*\|", n_rules),
        (status, "STATUS production rules", r"\|\s*Rules со статусом `production-tested`\s*\|\s*(\d+)\s*\|", n_production),
        (status, "STATUS fixture rules", r"\|\s*Rules со статусом `fixture-tested`\s*\|\s*(\d+)\s*\|", n_fixture),
        (status, "STATUS draft rules", r"\|\s*Rules со статусом `draft`\s*\|\s*(\d+)\s*\|", n_draft),
    ]
    for path, label, pattern, expected in checks:
        match = re.search(pattern, read(path))
        if not match:
            fail(f"{path.relative_to(ROOT)}: cannot find {label} (expected {expected})")
        claimed = int(match.group(1))
        if claimed != expected:
            fail(f"{path.relative_to(ROOT)}: {label} says {claimed}, real value is {expected}")


def validate_hook_wiring_json() -> None:
    """The hooks/README.md wiring block is copy-pasted into a real
    settings.json, so every ```json fence in it must parse."""
    import json

    hook_readme = ROOT / "hooks" / "README.md"
    blocks = re.findall(r"```json\n(.*?)\n```", read(hook_readme), re.DOTALL)
    if not blocks:
        fail("hooks/README.md has no ```json wiring block to validate")
    for i, block in enumerate(blocks):
        try:
            json.loads(block)
        except Exception as exc:  # noqa: BLE001 - validation script
            fail(f"hooks/README.md json block #{i} is invalid JSON: {exc}")


def main() -> None:
    validate_skill()
    validate_rules()
    validate_fixtures()
    validate_forward_results()
    validate_markdown_links()
    validate_doc_counts()
    validate_hook_wiring_json()
    print("validate_repo: ok")


if __name__ == "__main__":
    main()
