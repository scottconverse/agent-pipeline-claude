#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Autonomous-compliance check (v1.3.0: NO-OP STUB).

v1.2.1 scanned for autonomous-mode procedure deviations. v1.3.0
removed the autonomous-mode flow entirely; this check has nothing
to enforce. Kept as a no-op for backward compatibility.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_autonomous_compliance",
        description="Autonomous-compliance check (v1.3.0 no-op; always returns PASS).",
    )
    parser.add_argument("--run", help="Pipeline run id (accepted but ignored).")
    parser.add_argument(
        "--version",
        action="version",
        version="check_autonomous_compliance 1.3.0-noop",
    )
    parser.parse_args(argv)

    print(
        "OK: NO-OP -- autonomous-mode compliance check is inert in v1.3.0.\n"
        "  The grant + autonomous-mode flow was removed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
