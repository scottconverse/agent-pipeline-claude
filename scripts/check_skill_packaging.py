"""Validate installable Claude Code skills are self-contained.

Claude Code's plugin loader copies each ``skills/<name>/`` directory into a
discoverable location at install / cache time. A skill that references repo-root
files like ``../../commands/...`` works in the source tree but breaks once
copied to its own folder. This check verifies every installable skill only
references files bundled inside its own ``skills/<name>/`` directory.

Adapted from agent-pipeline-codex/scripts/check_skill_packaging.py.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
BACKTICK = re.compile(r"`([^`]+)`")


def referenced_paths(text: str) -> list[str]:
    refs: list[str] = []
    for match in BACKTICK.finditer(text):
        value = match.group(1).strip()
        if value.startswith("references/") or value.startswith("references\\"):
            refs.append(value)
    return refs


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        errors.append(f"{skill_dir}: missing SKILL.md")
        return errors

    text = skill_md.read_text(encoding="utf-8")

    if "../" in text or "..\\" in text:
        errors.append(f"{skill_md}: contains parent-directory traversal")

    for ref in referenced_paths(text):
        target = skill_dir / Path(ref)
        if not target.exists():
            errors.append(f"{skill_md}: missing bundled reference {ref}")

    return errors


def check_installed_copy(skill_dir: Path) -> list[str]:
    """Simulate the loader copying just skills/<name>/ into a fresh location."""
    with tempfile.TemporaryDirectory(prefix="agent-pipeline-claude-skill-install-") as tmp:
        install_root = Path(tmp) / "skills" / skill_dir.name
        shutil.copytree(skill_dir, install_root)
        return check_skill(install_root)


def main() -> int:
    if not SKILLS.exists():
        print("SKILL-PACKAGING: FAILED")
        print(f"- skills/ directory not found at {SKILLS}")
        return 1

    errors: list[str] = []
    skills_seen = 0
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        skills_seen += 1
        skill_dir = skill_md.parent
        errors.extend(check_skill(skill_dir))
        errors.extend(check_installed_copy(skill_dir))

    if skills_seen == 0:
        print("SKILL-PACKAGING: FAILED")
        print(f"- no skills found under {SKILLS}")
        return 1

    if errors:
        print("SKILL-PACKAGING: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"SKILL-PACKAGING: PASSED ({skills_seen} skill{'s' if skills_seen != 1 else ''} validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
