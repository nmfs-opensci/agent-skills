#!/usr/bin/env python3
"""Validate skill bundles and their evaluation directories."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
EVALS = ROOT / "evals"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "OpenAI API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
}


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"{path.relative_to(ROOT)}: cannot read UTF-8 text ({exc})"]

    if not lines or lines[0] != "---":
        return {}, [f"{path.relative_to(ROOT)}: YAML frontmatter must come first"]

    try:
        closing = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path.relative_to(ROOT)}: YAML frontmatter is not closed"]

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:closing], start=2):
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(
                f"{path.relative_to(ROOT)}:{line_number}: invalid frontmatter field"
            )
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        if key in fields:
            errors.append(
                f"{path.relative_to(ROOT)}:{line_number}: duplicate field '{key}'"
            )
        fields[key] = value.strip("\"'")

    unsupported = sorted(set(fields) - {"name", "description"})
    if unsupported:
        errors.append(
            f"{path.relative_to(ROOT)}: unsupported frontmatter field(s): "
            + ", ".join(unsupported)
        )
    for required in ("name", "description"):
        if not fields.get(required):
            errors.append(
                f"{path.relative_to(ROOT)}: missing frontmatter field '{required}'"
            )
    return fields, errors


def validate_skills() -> list[str]:
    errors: list[str] = []
    if not SKILLS.exists():
        return errors

    for skill_dir in sorted(path for path in SKILLS.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        all_skill_files = list(skill_dir.rglob("SKILL.md"))
        if not skill_file.is_file():
            errors.append(f"{skill_dir.relative_to(ROOT)}: missing SKILL.md")
            continue
        if len(all_skill_files) != 1:
            errors.append(
                f"{skill_dir.relative_to(ROOT)}: must contain exactly one SKILL.md"
            )

        fields, frontmatter_errors = parse_frontmatter(skill_file)
        errors.extend(frontmatter_errors)
        name = fields.get("name", "")
        if name and not NAME_PATTERN.fullmatch(name):
            errors.append(f"{skill_file.relative_to(ROOT)}: invalid skill name '{name}'")
        if name and name != skill_dir.name:
            errors.append(
                f"{skill_file.relative_to(ROOT)}: name '{name}' does not match "
                f"directory '{skill_dir.name}'"
            )
        if not NAME_PATTERN.fullmatch(skill_dir.name):
            errors.append(
                f"{skill_dir.relative_to(ROOT)}: directory name must use lowercase "
                "letters, digits, and single hyphens"
            )
    return errors


def validate_evaluations() -> list[str]:
    if not EVALS.exists():
        return []
    return [
        f"{evaluation.relative_to(ROOT)}: no corresponding skill"
        for evaluation in sorted(path for path in EVALS.iterdir() if path.is_dir())
        if not (SKILLS / evaluation.name / "SKILL.md").is_file()
    ]


def scan_for_secrets() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{path.relative_to(ROOT)}: possible {label}")
    return errors


def main() -> int:
    errors = validate_skills() + validate_evaluations() + scan_for_secrets()
    if errors:
        print("Skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Skill validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
