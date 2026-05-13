#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run every policy check and produce a combined PROMOTE/BLOCK report.

Wired into ``.pipelines/feature.yaml`` and ``.pipelines/bugfix.yaml`` as
the ``policy`` stage. The manager role uses this report to decide
PROMOTE / BLOCK / REPLAN.

Exit code: 0 only if every check passes. 1 if any check fails. The final
report line is one of:
  POLICY: ALL CHECKS PASSED
  POLICY: <N> CHECK(S) FAILED

To add project-specific policy checks, drop them in this directory next
to the generic ones and add them to the CHECKS list below.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

# Order matters only for human readability of the combined report.
# Add project-specific checks here (e.g., a custom check_module_boundaries.py).
CHECKS: list[tuple[str, list[str]]] = [
    ("check_manifest_schema", ["check_manifest_schema.py"]),
    # v1.2.0: cross-stage integrity — manifest SHA must match the pin
    # taken at preflight. Catches mid-run manifest mutation.
    ("check_manifest_immutable", ["check_manifest_immutable.py", "--check"]),
    ("check_allowed_paths", ["check_allowed_paths.py"]),
    ("check_no_todos", ["check_no_todos.py"]),
    ("check_adr_gate", ["check_adr_gate.py"]),
    # v1.2.0: STAGE_DONE markers required through `execute` by policy stage.
    ("check_stage_done", ["check_stage_done.py", "--through", "execute"]),
]


def _run(check_name: str, script_args: list[str], extra_args: list[str]) -> tuple[bool, str]:
    cmd = [sys.executable, str(THIS_DIR / script_args[0]), *script_args[1:], *extra_args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        help="Pipeline run id, passed through to checks that consume the manifest.",
    )
    args = parser.parse_args()

    extra_for_run_consumers = ["--run", args.run] if args.run else []
    # Checks that consume the run id (read manifest at .agent-runs/<run>/manifest.yaml).
    run_consumers = {
        "check_allowed_paths",
        "check_manifest_schema",
        "check_manifest_immutable",
        "check_stage_done",
    }

    results: list[tuple[str, bool, str]] = []
    for name, script_args in CHECKS:
        extra = extra_for_run_consumers if name in run_consumers else []
        passed, output = _run(name, script_args, extra)
        results.append((name, passed, output))

    print("=" * 64)
    print("Policy checks")
    print("=" * 64)
    for name, passed, output in results:
        status = "PASS" if passed else "FAIL"
        print(f"\n[{status}] {name}")
        if output:
            for line in output.splitlines():
                print(f"  {line}")

    failed = [name for name, passed, _ in results if not passed]
    print()
    print("-" * 64)
    if failed:
        print(f"POLICY: {len(failed)} CHECK(S) FAILED")
        for name in failed:
            print(f"  - {name}")
        return 1

    print("POLICY: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
