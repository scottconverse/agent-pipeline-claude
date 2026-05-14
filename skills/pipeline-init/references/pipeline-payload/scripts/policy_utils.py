#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for Agent Pipeline policy and gate scripts.

Centralizes logic that was previously duplicated across
`auto_promote.py`, `check_allowed_paths.py`, `check_no_todos.py`,
`check_adr_gate.py`, etc. — primarily the repo-root resolver that has
to handle both the plugin-source layout and the installed-project
layout (where `/pipeline-init` copies scripts under `scripts/policy/`).

Ported from agent-pipeline-codex (sibling implementation) in v1.2.2 so
that any policy script can `from policy_utils import find_repo_root`
without re-implementing the same logic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def find_repo_root(script_file: str) -> Path:
    """Resolve the repo root for both supported policy-script layouts.

    Supported layouts:
      * **Plugin source** — `<repo>/scripts/<script>.py` → repo root is
        the parent of `scripts/`.
      * **Installed project** — `<repo>/scripts/policy/<script>.py`
        (after `/pipeline-init` copies scripts) → repo root is two
        directories up.

    Falls back to `git rev-parse --show-toplevel` if neither layout
    matches (e.g., a developer is running the script from a non-standard
    location). Final fallback is `script_dir.parent` so the function
    always returns a Path even outside a git checkout.
    """
    script_dir = Path(script_file).resolve().parent
    if script_dir.name == "policy" and script_dir.parent.name == "scripts":
        return script_dir.parents[1]
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=script_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip())
    return script_dir.parent
