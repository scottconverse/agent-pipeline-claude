#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Priority-drift gate.

Reads the project's control-plane document and verifies the run manifest's
`advances_target` field names an authorized target. If the manifest names
work that the control plane explicitly excludes from the current active
scope, the script EXITs non-zero with a `PRIORITY_DRIFT` error.

Hard rule for v1.2.0: this gate runs BEFORE the researcher stage. The
failure mode it prevents is choosing the wrong work — drafter takes the
human's task description verbatim and never asks "is this the active
priority?" The active priority is set by the project's control plane;
this script enforces that the manifest aligns.

Control plane discovery (first match wins):

  1. .agent-workflows/PROJECT_CONTROL_PLANE.md
  2. .agent-workflows/ACTIVE_WORK_QUEUE.md
  3. docs/RELEASE_PLAN.md
  4. docs/PROJECT_CONTROL_PLANE.md

If none of these exist, the gate is informational — emits a WARN but
does not block. Projects without governance docs can still use the
pipeline; they just don't get this defense layer.

Active target extraction:

Looks for these headings (case-insensitive, first match wins):

  - "## Active target" / "## Active Target"
  - "## Current Scope Boundary" + first "Active target:" line under it
  - "## Active Target #1"
  - "Active target:" anywhere (last-resort scan)

The first line of prose under the heading is taken as the target string,
stripped of leading bullets, numbering, and quote-style markers.

Override semantics:

If the manifest has `override_active_target` as a non-empty string of
at least 60 characters (rough minimum for "two sentences worth of
reason"), the gate logs the override to
`.agent-workflows/scope-overrides.md` and exits 0 with status
OVERRIDE_ACCEPTED. The presence of override does NOT silence the
check — it logs visibly.

Usage:

    python scripts/check_active_target.py --run <run-id>

    # Or against an explicit manifest path:
    python scripts/check_active_target.py --manifest path/to/manifest.yaml

    # Override the control-plane discovery path:
    python scripts/check_active_target.py --run <id> \\
        --control-plane .agent-workflows/PROJECT_CONTROL_PLANE.md

Exit codes:

    0  — manifest's advances_target aligns with control plane's active target,
         OR a sufficient override is in place,
         OR no control plane exists (informational mode)
    1  — PRIORITY_DRIFT: manifest's advances_target does not align
    2  — schema error: manifest missing required fields
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Stdlib-only — minimal-yaml parser like check_manifest_schema.py uses.
try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


CONTROL_PLANE_CANDIDATES = (
    ".agent-workflows/PROJECT_CONTROL_PLANE.md",
    ".agent-workflows/ACTIVE_WORK_QUEUE.md",
    "docs/RELEASE_PLAN.md",
    "docs/PROJECT_CONTROL_PLANE.md",
)

ACTIVE_TARGET_HEADING_PATTERNS = (
    re.compile(r"^##+\s+Active Target(?:\s*#?\d*)?\s*$", re.IGNORECASE),
    re.compile(r"^##+\s+Current Scope Boundary\s*$", re.IGNORECASE),
    re.compile(r"^##+\s+Active Targets?\s*$", re.IGNORECASE),
)

INLINE_ACTIVE_TARGET_PATTERN = re.compile(
    r"^\s*Active target:\s*(?P<target>.+?)\s*$", re.IGNORECASE
)

OVERRIDE_MIN_CHARS = 60


@dataclass
class ControlPlaneState:
    path: Path | None
    active_target: str | None
    raw_excerpt: str | None  # the text around where the target was found, for citation


@dataclass
class GateResult:
    status: str  # ALIGNED | DRIFT | OVERRIDE_ACCEPTED | NO_CONTROL_PLANE | SCHEMA_ERROR
    message: str
    exit_code: int


def _find_repo_root() -> Path:
    """Walk up from cwd looking for .git or pyproject.toml as anchor."""
    p = Path.cwd().resolve()
    for parent in (p, *p.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return p


def _read_yaml(path: Path) -> dict:
    if yaml is None:
        # Minimal fallback — only handles the flat-key shape we need.
        # The full schema validator (check_manifest_schema.py) is the
        # authoritative parser; this is the cheap-and-cheerful path.
        result: dict[str, str | list[str]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)
            if not m:
                continue
            k, v = m.group(1), m.group(2).strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            result[k] = v
        return result
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _strip_target_string(raw: str) -> str:
    """Normalize an extracted target string for comparison.

    Removes leading numbering ("1. "), bullets, asterisks, surrounding
    code-quote backticks, and trailing punctuation that isn't load-bearing.
    Lowercases for case-insensitive comparison.
    """
    s = raw.strip()
    # Strip leading list-marker artifacts
    s = re.sub(r"^[\-\*\d\.\s]+", "", s)
    # Strip surrounding markdown bold/code
    s = re.sub(r"^\*+|\*+$", "", s).strip()
    s = re.sub(r"^`+|`+$", "", s).strip()
    # Trailing trivia
    s = re.sub(r"[\.\!:;,]+$", "", s).strip()
    return s


def _discover_control_plane(repo_root: Path, override_path: str | None) -> Path | None:
    if override_path:
        p = (repo_root / override_path).resolve()
        return p if p.exists() else None
    for candidate in CONTROL_PLANE_CANDIDATES:
        p = (repo_root / candidate).resolve()
        if p.exists():
            return p
    return None


def _extract_active_target(control_plane: Path) -> ControlPlaneState:
    """Locate the active-target line in the control-plane doc.

    Strategy:
      1. Look for a heading matching ACTIVE_TARGET_HEADING_PATTERNS.
         The first non-blank line under it (after numbering strip) is the target.
      2. If no matching heading, scan for "Active target:" inline.
      3. Return the first match found.
    """
    text = control_plane.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Strategy 1: heading-anchored
    for i, line in enumerate(lines):
        if any(pat.match(line) for pat in ACTIVE_TARGET_HEADING_PATTERNS):
            # Walk forward looking for first non-blank line
            for j in range(i + 1, min(i + 12, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                # Skip horizontal rules
                if re.match(r"^-{3,}$", candidate):
                    continue
                # If we hit another heading, stop — heading had no body
                if candidate.startswith("#"):
                    break
                # Sometimes the active target is named on a line like
                # "Active target: Installer/macOS certification follow-up."
                inline_match = INLINE_ACTIVE_TARGET_PATTERN.match(lines[j])
                if inline_match:
                    target = _strip_target_string(inline_match.group("target"))
                else:
                    target = _strip_target_string(candidate)
                if target:
                    excerpt = "\n".join(lines[max(0, i): min(len(lines), j + 2)])
                    return ControlPlaneState(
                        path=control_plane,
                        active_target=target,
                        raw_excerpt=excerpt,
                    )

    # Strategy 2: inline scan
    for i, line in enumerate(lines):
        m = INLINE_ACTIVE_TARGET_PATTERN.match(line)
        if m:
            target = _strip_target_string(m.group("target"))
            if target:
                excerpt = "\n".join(lines[max(0, i - 1): min(len(lines), i + 3)])
                return ControlPlaneState(
                    path=control_plane,
                    active_target=target,
                    raw_excerpt=excerpt,
                )

    return ControlPlaneState(path=control_plane, active_target=None, raw_excerpt=None)


def _targets_align(manifest_value: str, control_plane_target: str) -> bool:
    """Compare manifest's advances_target against the extracted target.

    Loose match: case-insensitive, whitespace-collapsed, punctuation-stripped.
    A manifest target is considered aligned if it's a substring of the
    control-plane target OR the control-plane target is a substring of the
    manifest target. This handles "Active target: Installer/macOS certification
    follow-up" matching a manifest that says "Installer/macOS certification".
    """
    def normalize(s: str) -> str:
        s = s.lower()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[^a-z0-9 /-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    m = normalize(manifest_value)
    c = normalize(control_plane_target)
    if not m or not c:
        return False
    return m in c or c in m


def _log_override(repo_root: Path, run_id: str, manifest_target: str, override_reason: str) -> None:
    ledger = repo_root / ".agent-workflows" / "scope-overrides.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"\n## {ts} — run {run_id}\n\n"
        f"- Manifest's `advances_target`: `{manifest_target}`\n"
        f"- Override reason (verbatim):\n\n"
        f"  > {override_reason.strip()}\n"
    )
    if not ledger.exists():
        ledger.write_text(
            "# Scope override ledger\n\n"
            "Every manifest that bypassed `check_active_target.py` via "
            "`override_active_target` is logged here.\n",
            encoding="utf-8",
        )
    with ledger.open("a", encoding="utf-8") as f:
        f.write(entry)


def evaluate(
    manifest_path: Path,
    repo_root: Path,
    control_plane_override: str | None = None,
    run_id: str | None = None,
) -> GateResult:
    """Run the priority-drift gate against a manifest.

    Returns a GateResult with one of five status values:
      ALIGNED            — manifest target matches control plane (exit 0)
      OVERRIDE_ACCEPTED  — override field present and sufficient (exit 0)
      DRIFT              — manifest target does not match control plane (exit 1)
      NO_CONTROL_PLANE   — no control plane found (exit 0, info)
      SCHEMA_ERROR       — manifest missing advances_target (exit 2)
    """
    if not manifest_path.exists():
        return GateResult(
            status="SCHEMA_ERROR",
            message=f"manifest not found: {manifest_path}",
            exit_code=2,
        )

    try:
        manifest = _read_yaml(manifest_path)
    except Exception as e:
        return GateResult(
            status="SCHEMA_ERROR",
            message=f"manifest parse error: {e}",
            exit_code=2,
        )

    pipeline_run = manifest.get("pipeline_run", manifest) if isinstance(manifest, dict) else {}
    if not isinstance(pipeline_run, dict):
        return GateResult(
            status="SCHEMA_ERROR",
            message="manifest pipeline_run section missing or malformed",
            exit_code=2,
        )

    advances_target = pipeline_run.get("advances_target")
    if not isinstance(advances_target, str) or not advances_target.strip():
        return GateResult(
            status="SCHEMA_ERROR",
            message=(
                "manifest.pipeline_run.advances_target is required (v1.2.0+). "
                "Set it to the exact 'Active target:' string from your control plane."
            ),
            exit_code=2,
        )

    override = pipeline_run.get("override_active_target")
    if isinstance(override, str) and len(override.strip()) >= OVERRIDE_MIN_CHARS:
        _log_override(
            repo_root,
            run_id or pipeline_run.get("id", "unknown"),
            advances_target,
            override,
        )
        return GateResult(
            status="OVERRIDE_ACCEPTED",
            message=(
                f"OVERRIDE_ACCEPTED — advances_target='{advances_target}' bypasses the gate. "
                f"Logged to .agent-workflows/scope-overrides.md. "
                f"At the manifest gate, type OVERRIDE-CONFIRMED to proceed."
            ),
            exit_code=0,
        )

    cp_path = _discover_control_plane(repo_root, control_plane_override)
    if cp_path is None:
        return GateResult(
            status="NO_CONTROL_PLANE",
            message=(
                "WARN: no control plane found at any of these paths:\n"
                + "\n".join(f"  {p}" for p in CONTROL_PLANE_CANDIDATES)
                + "\nGate is informational only. Skipping priority-drift check.\n"
                f"manifest.advances_target='{advances_target}' accepted without comparison."
            ),
            exit_code=0,
        )

    state = _extract_active_target(cp_path)
    if state.active_target is None:
        return GateResult(
            status="NO_CONTROL_PLANE",
            message=(
                f"WARN: control plane at {cp_path} exists but no 'Active target:' "
                "heading or inline line was found. Gate is informational. "
                f"manifest.advances_target='{advances_target}' accepted."
            ),
            exit_code=0,
        )

    if _targets_align(advances_target, state.active_target):
        return GateResult(
            status="ALIGNED",
            message=(
                f"ALIGNED — manifest.advances_target='{advances_target}' "
                f"matches control plane active target='{state.active_target}' "
                f"at {cp_path}"
            ),
            exit_code=0,
        )

    return GateResult(
        status="DRIFT",
        message=(
            "PRIORITY_DRIFT — manifest.advances_target does not align with control plane.\n\n"
            f"  manifest.advances_target:      {advances_target!r}\n"
            f"  control plane active target:   {state.active_target!r}\n"
            f"  control plane path:            {cp_path}\n\n"
            "Control plane excerpt:\n\n"
            + "\n".join(f"  | {line}" for line in (state.raw_excerpt or "").splitlines())
            + "\n\n"
            "Two acceptable paths to resolve:\n"
            "  1. Update the manifest's advances_target to match the active target.\n"
            "  2. Add a 2+ sentence override_active_target reason to the manifest.\n"
            "     The override will be logged to .agent-workflows/scope-overrides.md\n"
            "     and surface at the manifest gate for explicit confirmation."
        ),
        exit_code=1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_active_target",
        description="Verify the manifest's advances_target aligns with the project's active target.",
    )
    parser.add_argument(
        "--run",
        help="Pipeline run id (directory under .agent-runs/). Reads .agent-runs/<run>/manifest.yaml.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to a manifest YAML directly. Overrides --run.",
    )
    parser.add_argument(
        "--control-plane",
        help="Override control-plane path. Default: auto-discover.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="check_active_target 1.2.0",
    )
    args = parser.parse_args(argv)

    repo_root = _find_repo_root()

    if args.manifest:
        manifest_path = args.manifest.resolve()
        run_id = args.run
    elif args.run:
        manifest_path = (repo_root / ".agent-runs" / args.run / "manifest.yaml").resolve()
        run_id = args.run
    else:
        # No-op mode — like check_manifest_schema.py, this is a pipeline-runner-friendly default.
        return 0

    result = evaluate(
        manifest_path=manifest_path,
        repo_root=repo_root,
        control_plane_override=args.control_plane,
        run_id=run_id,
    )

    if result.status == "ALIGNED":
        print(f"OK: {result.message}")
    elif result.status == "OVERRIDE_ACCEPTED":
        print(f"WARN: {result.message}", file=sys.stderr)
    elif result.status == "NO_CONTROL_PLANE":
        print(result.message, file=sys.stderr)
    elif result.status == "DRIFT":
        print(result.message, file=sys.stderr)
    elif result.status == "SCHEMA_ERROR":
        print(f"ERROR: {result.message}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
