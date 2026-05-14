#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Autonomous-mode authorization gate.

v1.2.1 hardening: when the manifest sets `gate_policy: autonomous`, the
three human-approval gates (manifest / plan / manager) are configured to
skip chat-APPROVE and proceed on the LLM's own recommendation. This is
a substantial authority delegation and must NOT be enabled by
conversational consent alone — the v1.2.0 failure mode this addresses
was an LLM (me) refusing to honor conversational autonomous-mode
authorization. The fix is to make the authorization a structural file
that the LLM cannot interpret away.

This script validates the grant file referenced by the manifest. The
grant is a markdown document at `.agent-workflows/autonomous-grants/`
with required headers (Granted-by, Granted-at, Expires-at, etc.).
Without a valid grant, autonomous mode is impossible; the run halts at
preflight.

Status values returned (printed to stdout, also written to
`.agent-runs/<run-id>/autonomous-mode.log` when --run is provided):

  HUMAN-MODE              — manifest has gate_policy=human or omitted.
                            Nothing else to check. Exit 0.
  AUTONOMOUS-ACTIVE       — manifest cites a valid grant; autonomous mode
                            is on for the listed gates. Exit 0.
  NO_GRANT_FILE           — manifest claims autonomous mode but
                            autonomous_grant points at a non-existent
                            file. Exit 1.
  GRANT_EXPIRED           — grant's Expires-at is in the past. Exit 1.
  GRANT_REVOKED           — grant's Revoked: field is true. Exit 1.
  GRANT_MALFORMED         — grant file exists but lacks required headers
                            or has unparseable timestamps. Exit 1.

Usage:

    python scripts/check_autonomous_mode.py --run <run-id>
    python scripts/check_autonomous_mode.py --manifest path/to/manifest.yaml
    python scripts/check_autonomous_mode.py --grant path/to/grant.md
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


GRANT_REQUIRED_HEADERS = (
    "Granted-by",
    "Granted-at",
    "Expires-at",
    "Authorized-gates",
    "Forbidden-actions",
    "Revoked",
    "Rationale",
)


@dataclass
class GrantState:
    status: str
    grant_path: Path | None
    granted_by: str | None = None
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    revoked: bool = False
    authorized_gates: list[str] | None = None
    forbidden_actions: list[str] | None = None
    rationale: str | None = None
    error: str | None = None


def _find_repo_root() -> Path:
    p = Path.cwd().resolve()
    for parent in (p, *p.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return p


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    if yaml is None:
        # Stdlib-friendly minimal parse — only need a couple of flat keys
        text = path.read_text(encoding="utf-8")
        result: dict[str, str] = {}
        in_block = False
        for line in text.splitlines():
            if line.strip() == "pipeline_run:":
                in_block = True
                continue
            if in_block:
                m = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)
                if m:
                    k, v = m.group(1), m.group(2).strip().strip('"').strip("'")
                    if v and not v.startswith("["):
                        result[k] = v
        return {"pipeline_run": result}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _parse_grant_headers(text: str) -> dict[str, str]:
    """Extract the front-matter-style headers from a grant file.

    Headers are lines like `Granted-by: Scott Converse` at the top of
    the file. Stops at the first blank line + heading, or at first
    `## History` marker.
    """
    headers: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("##") and "History" in line:
            break
        m = re.match(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*:\s*(?P<val>.+)$", line)
        if m:
            headers[m.group("key")] = m.group("val").strip()
    return headers


def _parse_iso(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp, accepting trailing Z."""
    if not value:
        return None
    v = value.strip()
    # Accept "2026-05-14T03:00:00Z" by replacing Z → +00:00
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except (ValueError, TypeError):
        return None


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "1", "on")


def _parse_list_field(headers: dict[str, str], key: str) -> list[str]:
    """A header value like 'manifest, plan, manager' becomes ['manifest', 'plan', 'manager'].

    Also accepts multi-line bullet form parsed elsewhere if needed.
    """
    raw = headers.get(key, "")
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def evaluate_grant(grant_path: Path, now: datetime | None = None) -> GrantState:
    if now is None:
        now = datetime.now(timezone.utc)
    if not grant_path.exists():
        return GrantState(status="NO_GRANT_FILE", grant_path=grant_path,
                          error=f"grant file does not exist: {grant_path}")
    text = grant_path.read_text(encoding="utf-8")
    headers = _parse_grant_headers(text)

    missing = [h for h in GRANT_REQUIRED_HEADERS if h not in headers]
    if missing:
        return GrantState(
            status="GRANT_MALFORMED",
            grant_path=grant_path,
            error=f"grant file missing required headers: {', '.join(missing)}",
        )

    granted_at = _parse_iso(headers["Granted-at"])
    expires_at = _parse_iso(headers["Expires-at"])
    if granted_at is None or expires_at is None:
        return GrantState(
            status="GRANT_MALFORMED",
            grant_path=grant_path,
            granted_by=headers.get("Granted-by"),
            error=(
                "grant has unparseable timestamp(s): "
                f"Granted-at={headers['Granted-at']!r} "
                f"Expires-at={headers['Expires-at']!r}"
            ),
        )

    revoked = _parse_bool(headers["Revoked"])
    state = GrantState(
        status="",
        grant_path=grant_path,
        granted_by=headers.get("Granted-by"),
        granted_at=granted_at,
        expires_at=expires_at,
        revoked=revoked,
        authorized_gates=_parse_list_field(headers, "Authorized-gates"),
        forbidden_actions=_parse_list_field(headers, "Forbidden-actions"),
        rationale=headers.get("Rationale"),
    )

    if revoked:
        state.status = "GRANT_REVOKED"
        state.error = "grant has Revoked: true"
        return state

    if now >= expires_at:
        state.status = "GRANT_EXPIRED"
        state.error = f"grant expired at {expires_at.isoformat()} (now: {now.isoformat()})"
        return state

    if now < granted_at:
        state.status = "GRANT_MALFORMED"
        state.error = (
            f"grant Granted-at is in the future ({granted_at.isoformat()}); "
            "this is either a clock-skew issue or a typo"
        )
        return state

    state.status = "AUTONOMOUS-ACTIVE"
    return state


def evaluate_manifest(
    manifest_path: Path,
    repo_root: Path,
    now: datetime | None = None,
) -> GrantState:
    manifest = _read_manifest(manifest_path)
    pipeline_run = manifest.get("pipeline_run", {}) if isinstance(manifest, dict) else {}
    if not isinstance(pipeline_run, dict):
        pipeline_run = {}
    gate_policy = pipeline_run.get("gate_policy", "human")
    if isinstance(gate_policy, str):
        gate_policy = gate_policy.strip().lower()

    if gate_policy != "autonomous":
        return GrantState(status="HUMAN-MODE", grant_path=None)

    grant_rel = pipeline_run.get("autonomous_grant", "")
    if not isinstance(grant_rel, str) or not grant_rel.strip():
        return GrantState(
            status="NO_GRANT_FILE",
            grant_path=None,
            error=(
                "manifest has gate_policy: autonomous but no autonomous_grant path. "
                "Set autonomous_grant to the path of your grant file under "
                ".agent-workflows/autonomous-grants/."
            ),
        )

    grant_path = (repo_root / grant_rel).resolve()
    return evaluate_grant(grant_path, now=now)


def _grant_sha256(grant_path: Path) -> str | None:
    """Hash the grant file's bytes. Returns None if the file is unreadable."""
    try:
        return hashlib.sha256(grant_path.read_bytes()).hexdigest()
    except OSError:
        return None


def _write_log(run_dir: Path, state: GrantState) -> None:
    """Append a line to autonomous-mode.log recording the grant decision.

    v1.2.2: when the grant validates as AUTONOMOUS-ACTIVE, the line
    also records `grant_sha=<sha256>` so the post-run compliance check
    can detect mid-run grant tampering. Older logs without grant_sha
    are tolerated for back-compat (compliance check skips the SHA
    comparison silently in that case).
    """
    log = run_dir / "autonomous-mode.log"
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts}  status={state.status}"
    if state.grant_path is not None:
        line += f"  grant={state.grant_path}"
    if state.status == "AUTONOMOUS-ACTIVE" and state.grant_path is not None:
        sha = _grant_sha256(state.grant_path)
        if sha is not None:
            line += f"  grant_sha={sha}"
    if state.error:
        line += f"  error={state.error!r}"
    with log.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_autonomous_mode",
        description="Validate autonomous-mode grant for a pipeline run.",
    )
    parser.add_argument(
        "--run",
        help="Pipeline run id (directory under .agent-runs/).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to manifest YAML directly. Overrides --run.",
    )
    parser.add_argument(
        "--grant",
        type=Path,
        help="Validate a grant file directly without going through a manifest.",
    )
    parser.add_argument(
        "--version", action="version", version="check_autonomous_mode 1.2.2"
    )
    args = parser.parse_args(argv)

    repo_root = _find_repo_root()

    if args.grant:
        state = evaluate_grant(args.grant.resolve())
    elif args.manifest:
        state = evaluate_manifest(args.manifest.resolve(), repo_root)
    elif args.run:
        manifest = (repo_root / ".agent-runs" / args.run / "manifest.yaml").resolve()
        state = evaluate_manifest(manifest, repo_root)
        run_dir = (repo_root / ".agent-runs" / args.run).resolve()
        if run_dir.exists():
            _write_log(run_dir, state)
    else:
        return 0  # no-op when invoked without args

    if state.status == "HUMAN-MODE":
        print("OK: HUMAN-MODE — manifest does not declare gate_policy: autonomous; no grant needed.")
        return 0

    if state.status == "AUTONOMOUS-ACTIVE":
        gates = ", ".join(state.authorized_gates or []) or "(none listed)"
        expires_left = (state.expires_at - datetime.now(timezone.utc)).total_seconds() / 3600 if state.expires_at else 0
        print(
            f"OK: AUTONOMOUS-ACTIVE\n"
            f"  grant:             {state.grant_path}\n"
            f"  granted-by:        {state.granted_by}\n"
            f"  granted-at:        {state.granted_at}\n"
            f"  expires-at:        {state.expires_at} ({expires_left:.1f}h remaining)\n"
            f"  authorized-gates:  {gates}\n"
            f"  forbidden-actions: {', '.join(state.forbidden_actions or []) or '(default high_risk set)'}\n"
        )
        return 0

    # Failure path
    print(f"AUTONOMOUS_MODE_GATE_FAILED: {state.status}", file=sys.stderr)
    if state.error:
        print(f"  {state.error}", file=sys.stderr)
    print(
        "\nTo enable autonomous mode you need a valid grant file at\n"
        "  .agent-workflows/autonomous-grants/<name>.md\n"
        "with required headers: " + ", ".join(GRANT_REQUIRED_HEADERS) + "\n"
        "Ask Claude in chat to write or update the grant.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
