# SPDX-License-Identifier: Apache-2.0
"""v1.3.0 contract: check_autonomous_mode.py is a no-op stub.

The grant + autonomous-mode flow was removed in v1.3.0. The script
is kept so existing pipeline yamls that reference it still work,
but it always exits 0 with status HUMAN-MODE regardless of input.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_autonomous_mode.py"


def _run(args=None):
    """Invoke the script directly via subprocess so we exercise the real CLI."""
    cmd = [sys.executable, str(SCRIPT)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def test_noop_with_no_args_returns_zero():
    r = _run()
    assert r.returncode == 0
    assert "HUMAN-MODE" in r.stdout
    assert "v1.3.0" in r.stdout


def test_noop_ignores_run_arg():
    r = _run(["--run", "anything"])
    assert r.returncode == 0
    assert "HUMAN-MODE" in r.stdout


def test_noop_ignores_grant_arg():
    r = _run(["--grant", "/nonexistent/path.md"])
    assert r.returncode == 0
    assert "HUMAN-MODE" in r.stdout


def test_noop_ignores_manifest_arg():
    r = _run(["--manifest", "/nonexistent/manifest.yaml"])
    assert r.returncode == 0
    assert "HUMAN-MODE" in r.stdout


def test_noop_ignores_all_args_together():
    r = _run(["--run", "x", "--manifest", "y", "--grant", "z"])
    assert r.returncode == 0
    assert "HUMAN-MODE" in r.stdout


def test_version_flag():
    r = _run(["--version"])
    assert r.returncode == 0
    assert "1.3.0-noop" in r.stdout


def test_help_flag():
    r = _run(["--help"])
    assert r.returncode == 0
    assert "no-op" in r.stdout.lower() or "always returns PASS" in r.stdout


def test_invalid_flag_still_fails_gracefully():
    """argparse rejects unknown flags with exit 2 — kept for sanity."""
    r = _run(["--bogus"])
    assert r.returncode == 2
