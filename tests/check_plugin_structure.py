"""Plugin structure validator.

Mirrors what a plugin loader does:
1. Walks the plugin tree for *.md and SKILL.md files
2. Parses YAML frontmatter
3. Verifies required fields per file type
4. Reports every issue with file + line context

Run before committing any frontmatter change. Catches the bugs that ship
without this validation: malformed argument-hint quoting, missing name field
in SKILL.md, drift between directory name and frontmatter name, etc.

Usage:
    python tests/check_plugin_structure.py
    Exit code 0 = clean. Exit code 1 = issues found.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required: pip install pyyaml\n")
    sys.exit(2)

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def extract_frontmatter(text: str) -> tuple[dict | None, str | None]:
    if not text.startswith("---"):
        return None, "no leading --- (file has no frontmatter)"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "frontmatter not closed (need second --- line)"
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {type(e).__name__}: {e}"
    if fm is None:
        return None, "frontmatter parsed to None (empty body between --- markers)"
    if not isinstance(fm, dict):
        return None, f"frontmatter is not a mapping (got {type(fm).__name__})"
    return fm, None


def check_skill(path: Path) -> list[str]:
    """skills/<name>/SKILL.md must have name (matching dir) and description."""
    errors: list[str] = []
    expected_name = path.parent.name
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, err = extract_frontmatter(text)
    if err:
        return [f"{path}: {err}"]
    if "name" not in fm:
        errors.append(f"{path}: missing required 'name' field in frontmatter")
    elif fm["name"] != expected_name:
        errors.append(
            f"{path}: name='{fm['name']}' does not match directory '{expected_name}'"
        )
    if "description" not in fm:
        errors.append(f"{path}: missing required 'description' field")
    body = text.split("---", 2)[2] if text.startswith("---") else text
    if len(body.strip()) < 50:
        errors.append(f"{path}: body is too short (likely empty or stub)")
    return errors


def check_command(path: Path) -> list[str]:
    """commands/<name>.md should have description (name optional, derived from filename)."""
    errors: list[str] = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return []
    fm, err = extract_frontmatter(text)
    if err:
        return [f"{path}: {err}"]
    if "description" not in fm:
        errors.append(f"{path}: missing recommended 'description' field")
    return errors


def check_role(path: Path) -> list[str]:
    """pipelines/roles/<role>.md may have frontmatter; if present, must parse."""
    errors: list[str] = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return []
    fm, err = extract_frontmatter(text)
    if err:
        errors.append(f"{path}: {err}")
    return errors


def check_pipeline_yaml(path: Path) -> list[str]:
    """pipelines/*.yaml must parse as YAML."""
    errors: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            errors.append(f"{path}: parsed to None")
    except yaml.YAMLError as e:
        errors.append(f"{path}: YAML parse error: {type(e).__name__}: {e}")
    return errors


def check_plugin_manifests(plugin_root: Path) -> list[str]:
    """plugin.json and marketplace.json must be valid JSON with required fields."""
    import json

    errors: list[str] = []
    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        errors.append(f"{plugin_json}: file does not exist (required)")
    else:
        try:
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            if "name" not in data:
                errors.append(f"{plugin_json}: missing required 'name' field")
        except json.JSONDecodeError as e:
            errors.append(f"{plugin_json}: invalid JSON: {e}")

    marketplace_json = plugin_root / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            data = json.loads(marketplace_json.read_text(encoding="utf-8"))
            if "plugins" in data:
                for p in data["plugins"]:
                    if "name" not in p:
                        errors.append(
                            f"{marketplace_json}: plugin entry missing 'name'"
                        )
        except json.JSONDecodeError as e:
            errors.append(f"{marketplace_json}: invalid JSON: {e}")
    return errors


def main() -> int:
    all_errors: list[str] = []

    # 1. Plugin manifest JSON
    all_errors.extend(check_plugin_manifests(PLUGIN_ROOT))

    # 2. Skills
    skills_dir = PLUGIN_ROOT / "skills"
    skill_count = 0
    if skills_dir.exists():
        for skill_md in skills_dir.glob("*/SKILL.md"):
            all_errors.extend(check_skill(skill_md))
            skill_count += 1

    # 3. Commands
    commands_dir = PLUGIN_ROOT / "commands"
    cmd_count = 0
    if commands_dir.exists():
        for cmd_md in commands_dir.glob("*.md"):
            all_errors.extend(check_command(cmd_md))
            cmd_count += 1

    # 4. Pipeline roles
    roles_dir = PLUGIN_ROOT / "pipelines" / "roles"
    role_count = 0
    if roles_dir.exists():
        for role_md in roles_dir.glob("*.md"):
            all_errors.extend(check_role(role_md))
            role_count += 1

    # 5. Pipeline YAMLs
    pipelines_dir = PLUGIN_ROOT / "pipelines"
    pipe_count = 0
    if pipelines_dir.exists():
        for pipe_yaml in pipelines_dir.glob("*.yaml"):
            all_errors.extend(check_pipeline_yaml(pipe_yaml))
            pipe_count += 1

    print("Plugin structure check")
    print(f"  skills:    {skill_count}")
    print(f"  commands:  {cmd_count}")
    print(f"  roles:     {role_count}")
    print(f"  pipelines: {pipe_count}")
    print()
    if all_errors:
        print(f"FOUND {len(all_errors)} ISSUE(S):")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
