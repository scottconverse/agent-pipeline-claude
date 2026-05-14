# SPDX-License-Identifier: Apache-2.0
"""v1.3.0 contract: check_autonomous_compliance.py is a no-op stub.

The post-run autonomous-compliance scan was removed in v1.3.0 along
with the autonomous-mode flow it policed. The script is kept so
run_all.py invocations still succeed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_autonomous_compliance.py"


def _run(args=None):
    cmd = [sys.executable, str(SCRIPT)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def test_noop_with_no_args_returns_zero():
    r = _run()
    assert r.returncode == 0
    assert "NO-OP" in r.stdout
    assert "v1.3.0" in r.stdout


def test_noop_ignores_run_arg():
    r = _run(["--run", "anything"])
    assert r.returncode == 0
    assert "NO-OP" in r.stdout


def test_noop_ignores_missing_run():
    r = _run(["--run", "/this/does/not/exist"])
    assert r.returncode == 0


def test_version_flag():
    r = _run(["--version"])
    assert r.returncode == 0
    assert "1.3.0-noop" in r.stdout


def test_help_flag():
    r = _run(["--help"])
    assert r.returncode == 0


def test_invalid_flag_fails_gracefully():
    r = _run(["--bogus"])
    assert r.returncode == 2
