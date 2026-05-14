"""Validate installable Claude Code skills are self-contained.

Claude Code's plugin loader copies each ``skills/<name>/`` directory into a
discoverable location at install / cache time. A skill that references repo-root
files like ``pipelines/templates/...`` works in the source tree but breaks once
the skill is loaded from its own folder. This check verifies every ``.md`` file
inside each skill (SKILL.md AND every file under ``references/``) only points
at files that are bundled inside that skill's own folder.

Adapted from agent-pipeline-codex/scripts/check_skill_packaging.py and deepened
in v1.1.0 to scan nested ``references/*.md`` recursively, not only SKILL.md.
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

# Plugin-owned paths that, if referenced inside a skill's runtime instructions,
# will not resolve from an installed cache. These MUST be bundled inside the
# skill folder (typically under references/).
#
# We deliberately exclude:
#   - `pipelines/templates/...` — handled by PLUGIN_TEMPLATE_LEAKS below with
#     a more specific message.
#   - `scripts/policy/...` — that's the path INSIDE the consumer's project after
#     `/pipeline-init` scaffolding; not our `scripts/`.
#
# We also exclude common consumer-project paths the skill READS at runtime
# (docs/, tests/, CLAUDE.md, etc.) because those live in the user's repo, not
# ours. The check is conservative: it only flags repo-root paths that are
# unambiguously plugin-owned.
PLUGIN_ASSET_LEAKS = re.compile(
    r"`((?:pipelines/(?!templates/)|scripts/(?!policy/))[^`]+)`"
)
PLUGIN_TEMPLATE_LEAKS = re.compile(r"`(pipelines/templates/[^`]+)`")

# Files inside the bundled payload (skills/pipeline-init/references/pipeline-payload/)
# are templates for the consumer's scaffolded project — paths inside them refer
# to the consumer's post-scaffold layout, not our plugin layout. Skip leak
# detection inside the payload tree.
PAYLOAD_MARKER = ("references", "pipeline-payload")


def referenced_paths(text: str) -> list[str]:
    refs: list[str] = []
    for match in BACKTICK.finditer(text):
        value = match.group(1).strip()
        if value.startswith("references/") or value.startswith("references\\"):
            refs.append(value)
    return refs


def is_payload_path(md: Path, skill_dir: Path) -> bool:
    """True if md lives inside skills/<name>/references/pipeline-payload/."""
    try:
        rel = md.relative_to(skill_dir).parts
    except ValueError:
        return False
    return len(rel) >= 2 and rel[0] == PAYLOAD_MARKER[0] and rel[1] == PAYLOAD_MARKER[1]


def check_one_md(md: Path, skill_dir: Path) -> list[str]:
    errors: list[str] = []
    text = md.read_text(encoding="utf-8")

    if "../" in text or "..\\" in text:
        errors.append(f"{md}: contains parent-directory traversal")

    # Bundled-reference resolution (always applies)
    for ref in referenced_paths(text):
        target = skill_dir / Path(ref)
        if not target.exists():
            errors.append(f"{md}: missing bundled reference {ref}")

    # Plugin-asset leak detection — skipped for files INSIDE the bundled
    # payload tree (those are templates for the consumer's project).
    if is_payload_path(md, skill_dir):
        return errors

    for match in PLUGIN_ASSET_LEAKS.finditer(text):
        leak = match.group(1)
        errors.append(
            f"{md}: references plugin-owned path `{leak}` — won't resolve from "
            f"installed cache; bundle inside the skill folder instead"
        )

    for match in PLUGIN_TEMPLATE_LEAKS.finditer(text):
        leak = match.group(1)
        errors.append(
            f"{md}: references plugin-owned template `{leak}` — bundle inside "
            f"the skill folder (e.g. references/<template>.md)"
        )

    return errors


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        errors.append(f"{skill_dir}: missing SKILL.md")
        return errors

    errors.extend(check_one_md(skill_md, skill_dir))

    for md in sorted(skill_dir.rglob("*.md")):
        if md == skill_md:
            continue
        errors.extend(check_one_md(md, skill_dir))

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

    print(f"SKILL-PACKAGING: PASSED ({skills_seen} skill{'s' if skills_seen != 1 else ''} validated, recursive scan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
