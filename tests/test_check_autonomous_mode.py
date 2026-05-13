"""Tests for scripts/check_autonomous_mode.py — v1.2.1 grant validation."""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_autonomous_mode as cam  # type: ignore  # noqa: E402


def _write_grant(
    tmp_path: Path,
    *,
    granted_at: datetime,
    expires_at: datetime,
    revoked: bool = False,
    name: str = "test-grant.md",
    skip_header: str | None = None,
) -> Path:
    grants_dir = tmp_path / ".agent-workflows" / "autonomous-grants"
    grants_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "Granted-by": "Scott Converse",
        "Granted-at": granted_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Expires-at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Scope": "test project",
        "Authorized-gates": "manifest-gate APPROVE, plan-gate APPROVE, manager-gate APPROVE (PROMOTE only)",
        "Forbidden-actions": "admin-merge any PR, tag push, release publish, force push, any action_class: high_risk",
        "Revoked": "true" if revoked else "false",
        "Rationale": "test rationale",
    }
    lines = ["# Autonomous grant — test", ""]
    for k, v in headers.items():
        if skip_header is not None and k == skip_header:
            continue
        lines.append(f"{k}: {v}")
    lines.extend(["", "## History", f"- {granted_at.isoformat()} — created (test)"])
    path = grants_dir / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_manifest(tmp_path: Path, **fields: object) -> Path:
    pipeline_run = {"id": "test-run", "type": "feature"}
    pipeline_run.update(fields)
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump({"pipeline_run": pipeline_run}), encoding="utf-8")
    return manifest


def test_human_mode_when_no_gate_policy(tmp_path: Path) -> None:
    """Manifest without gate_policy → HUMAN-MODE, no grant needed."""
    manifest = _write_manifest(tmp_path)
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "HUMAN-MODE"


def test_human_mode_when_explicitly_human(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, gate_policy="human")
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "HUMAN-MODE"


def test_autonomous_active_with_valid_grant(tmp_path: Path) -> None:
    """gate_policy=autonomous with valid in-window grant → AUTONOMOUS-ACTIVE."""
    now = datetime.now(timezone.utc)
    grant = _write_grant(
        tmp_path,
        granted_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=4),
    )
    manifest = _write_manifest(
        tmp_path,
        gate_policy="autonomous",
        autonomous_grant=str(grant.relative_to(tmp_path)),
    )
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "AUTONOMOUS-ACTIVE", state.error
    assert state.granted_by == "Scott Converse"
    assert "manifest-gate" in " ".join(state.authorized_gates or [])


def test_no_grant_file_when_path_missing(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        gate_policy="autonomous",
        autonomous_grant=".agent-workflows/autonomous-grants/does-not-exist.md",
    )
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "NO_GRANT_FILE"


def test_no_grant_file_when_path_empty(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, gate_policy="autonomous", autonomous_grant="")
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "NO_GRANT_FILE"


def test_grant_expired(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    grant = _write_grant(
        tmp_path,
        granted_at=now - timedelta(hours=12),
        expires_at=now - timedelta(hours=1),
    )
    manifest = _write_manifest(
        tmp_path,
        gate_policy="autonomous",
        autonomous_grant=str(grant.relative_to(tmp_path)),
    )
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "GRANT_EXPIRED"


def test_grant_revoked(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    grant = _write_grant(
        tmp_path,
        granted_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=4),
        revoked=True,
    )
    manifest = _write_manifest(
        tmp_path,
        gate_policy="autonomous",
        autonomous_grant=str(grant.relative_to(tmp_path)),
    )
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "GRANT_REVOKED"


def test_grant_malformed_missing_header(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    grant = _write_grant(
        tmp_path,
        granted_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=4),
        skip_header="Expires-at",
    )
    manifest = _write_manifest(
        tmp_path,
        gate_policy="autonomous",
        autonomous_grant=str(grant.relative_to(tmp_path)),
    )
    state = cam.evaluate_manifest(manifest, tmp_path)
    assert state.status == "GRANT_MALFORMED"
    assert "Expires-at" in (state.error or "")


def test_evaluate_grant_directly(tmp_path: Path) -> None:
    """evaluate_grant() works on a grant path without going through a manifest."""
    now = datetime.now(timezone.utc)
    grant = _write_grant(
        tmp_path,
        granted_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=4),
    )
    state = cam.evaluate_grant(grant)
    assert state.status == "AUTONOMOUS-ACTIVE"
