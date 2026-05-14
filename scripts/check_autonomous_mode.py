#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Autonomous-mode authorization gate (v1.3.0: NO-OP STUB).

v1.2.1 implemented a grant-based autonomous-mode gate. v1.3.0 removed
the grant system entirely; gates fire as modal AskUserQuestion prompts
instead, and auto-promote is the evidence-driven path to hands-off.

This script is kept as a no-op for backward compatibility. It always
returns PASS.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_autonomous_mode",
        description="Autonomous-mode gate (v1.3.0 no-op; always returns PASS).",
    )
    parser.add_argument("--run", help="Pipeline run id (accepted but ignored).")
    parser.add_argument("--manifest", help="Manifest path (accepted but ignored).")
    parser.add_argument("--grant", help="Grant path (accepted but ignored).")
    parser.add_argument(
        "--version", action="version", version="check_autonomous_mode 1.3.0-noop"
    )
    parser.parse_args(argv)

    print(
        "OK: HUMAN-MODE -- autonomous mode and grant system removed in v1.3.0.\n"
        "  The v1.3.0 run skill uses modal AskUserQuestion gates and\n"
        "  evidence-driven auto-promote. No grant needed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
