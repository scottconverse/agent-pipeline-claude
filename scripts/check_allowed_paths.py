#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Policy: changed files must fall inside `allowed_paths` and outside `forbidden_paths`.

Reads the pipeline manifest at `.agent-runs/<run-id>/manifest.yaml`,
compares the working-tree diff against the manifest's path lists, and
exits non-zero with evidence lines if any change is out of scope.

If invoked without --run, prints usage and exits 0 (so a developer can
run `python scripts/policy/run_all.py` on a clean working tree without
needing a live pipeline run).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / ".agent-runs"


def _git_changed_files() -> list[str]:
    """Return paths changed in the working tree relative to HEAD.

    Uses `git diff --name-only HEAD` which covers staged + unstaged + new
    files that have been added. Untracked files are NOT in this list by
    design — pipeline runs commit work-in-progress to the run branch
    before the policy stage fires.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _load_manifest_lists(manifest_path: Path) -> tuple[list[str], list[str]]:
    """Return (allowed_paths, forbidden_paths) parsed from manifest YAML.

    Stdlib-only: no PyYAML. The manifest format is a tightly-constrained
    subset (top-level `pipeline_run:` block, list values are simple
    strings under `- ` lines). A real YAML parse is not required for the
    fields this checker reads.
    """
    if not manifest_path.exists():
        print(f"FAIL: manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    text = manifest_path.read_text(encoding="utf-8")
    allowed: list[str] = []
    forbidden: list[str] = []
    current_key: str | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        # Strip comments after a `#` that is preceded by whitespace.
        if "#" in line:
            hash_idx = line.find("#")
            if hash_idx == 0 or line[hash_idx - 1].isspace():
                line = line[:hash_idx].rstrip()
        if not line:
            continue
        stripped = line.strip()
        # Track which list we're inside.
        if stripped.startswith("allowed_paths:"):
            current_key = "allowed"
            if "[]" in stripped:
                current_key = None
            continue
        if stripped.startswith("forbidden_paths:"):
            current_key = "forbidden"
            if "[]" in stripped:
                current_key = None
            continue
        # Detect any other top-level key — leaves the current list.
        if not raw.startswith((" ", "\t")) and stripped.endswith(":"):
            current_key = None
            continue
        if stripped.startswith("- ") and current_key is not None:
            value = stripped[2:].strip().strip("\"'")
            if current_key == "allowed":
                allowed.append(value)
            elif current_key == "forbidden":
                forbidden.append(value)
        elif current_key is not None and not stripped.startswith("- "):
            current_key = None

    return allowed, forbidden


def _is_under(path: str, prefixes: list[str]) -> bool:
    """True if `path` is exactly a prefix or starts with `prefix + "/"`."""
    for prefix in prefixes:
        if not prefix:
            continue
        normalized = prefix.rstrip("/")
        if path == normalized or path.startswith(normalized + "/"):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        help="Pipeline run id (directory under .agent-runs/). Without this, the check is a no-op.",
    )
    args = parser.parse_args()

    if not args.run:
        print(
            "check_allowed_paths: no --run argument provided; skipping (no-op outside a pipeline run)."
        )
        return 0

    manifest_path = RUN_DIR / args.run / "manifest.yaml"
    allowed, forbidden = _load_manifest_lists(manifest_path)

    if not allowed and not forbidden:
        print(
            "check_allowed_paths: manifest has empty allowed_paths AND forbidden_paths — "
            "no constraints to enforce. PASS."
        )
        return 0

    changed = _git_changed_files()
    if not changed:
        print("check_allowed_paths: no changed files in working tree. PASS.")
        return 0

    violations: list[tuple[str, str]] = []
    for path in changed:
        if forbidden and _is_under(path, forbidden):
            violations.append((path, "matches forbidden_paths"))
            continue
        if allowed and not _is_under(path, allowed):
            violations.append((path, "outside allowed_paths"))

    if violations:
        print("check_allowed_paths: FAIL")
        print(f"  manifest: {manifest_path}")
        print(f"  allowed_paths: {allowed or '(none)'}")
        print(f"  forbidden_paths: {forbidden or '(none)'}")
        print("  violations:")
        for path, reason in violations:
            print(f"    {path}  ({reason})")
        return 1

    print(f"check_allowed_paths: PASS — {len(changed)} changed file(s), all within allowed_paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
