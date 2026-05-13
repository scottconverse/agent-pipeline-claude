"""Tests for scripts/check_active_target.py — v1.2.0 priority-drift gate."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# Make sibling scripts importable for direct evaluate() calls
import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_active_target as cat  # type: ignore  # noqa: E402


def _write_manifest(dest: Path, **fields: object) -> Path:
    """Build a minimal manifest YAML with the fields supplied."""
    import yaml

    pipeline_run = {"id": "test-run", "type": "feature"}
    pipeline_run.update(fields)
    data = {"pipeline_run": pipeline_run}
    dest.write_text(yaml.safe_dump(data), encoding="utf-8")
    return dest


def _write_control_plane(repo: Path, body: str, name: str = "PROJECT_CONTROL_PLANE.md") -> Path:
    wf = repo / ".agent-workflows"
    wf.mkdir(parents=True, exist_ok=True)
    p = wf / name
    p.write_text(body, encoding="utf-8")
    return p


def test_aligned_target_passes(tmp_path: Path) -> None:
    """Manifest's advances_target matching control plane's active target → ALIGNED, exit 0."""
    _write_control_plane(
        tmp_path,
        textwrap.dedent(
            """\
            # CivicSuite Project Control Plane

            ## Current Scope Boundary

            Active target: Installer/macOS certification follow-up.

            Why next: ...
            """
        ),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Installer/macOS certification follow-up",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "ALIGNED", f"got {result.status}: {result.message}"
    assert result.exit_code == 0


def test_drift_blocks(tmp_path: Path) -> None:
    """Manifest naming work outside the active target → DRIFT, exit 1."""
    _write_control_plane(
        tmp_path,
        textwrap.dedent(
            """\
            ## Active target

            Installer/macOS certification follow-up
            """
        ),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Add workflow_dispatch trigger to civicrecords-ai release.yml",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "DRIFT"
    assert result.exit_code == 1
    assert "PRIORITY_DRIFT" in result.message


def test_substring_alignment(tmp_path: Path) -> None:
    """Loose match works — control plane string contains manifest string or vice versa."""
    _write_control_plane(
        tmp_path,
        "## Active target\n\nInstaller/macOS certification follow-up — phase 1\n",
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Installer/macOS certification follow-up",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "ALIGNED"


def test_no_control_plane_is_informational(tmp_path: Path) -> None:
    """No control plane → NO_CONTROL_PLANE warning, exit 0 (greenfield projects)."""
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="some target",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "NO_CONTROL_PLANE"
    assert result.exit_code == 0


def test_override_accepts_drift_with_sufficient_reason(tmp_path: Path) -> None:
    """override_active_target with 60+ chars bypasses the gate and logs the override."""
    _write_control_plane(
        tmp_path,
        "## Active target\n\nInstaller/macOS certification follow-up\n",
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Different work entirely",
        override_active_target=(
            "Hotfix path required for production blocker on civicrecords-ai. "
            "Active target work resumes immediately after this 30-minute side task."
        ),
    )
    result = cat.evaluate(manifest, tmp_path, run_id="test-override")
    assert result.status == "OVERRIDE_ACCEPTED"
    assert result.exit_code == 0
    ledger = tmp_path / ".agent-workflows" / "scope-overrides.md"
    assert ledger.exists()
    assert "test-override" in ledger.read_text(encoding="utf-8")


def test_override_too_short_does_not_apply(tmp_path: Path) -> None:
    """override_active_target with <60 chars is rejected as insufficient; drift still fires."""
    _write_control_plane(
        tmp_path,
        "## Active target\n\nInstaller/macOS certification follow-up\n",
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Different work entirely",
        override_active_target="too short",
    )
    result = cat.evaluate(manifest, tmp_path)
    # The short override is silently ignored; the drift check still runs and fails
    assert result.status == "DRIFT"
    assert result.exit_code == 1


def test_missing_advances_target_is_schema_error(tmp_path: Path) -> None:
    """Manifest without advances_target → SCHEMA_ERROR, exit 2."""
    _write_control_plane(tmp_path, "## Active target\n\nFoo\n")
    manifest = _write_manifest(tmp_path / "manifest.yaml")
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "SCHEMA_ERROR"
    assert result.exit_code == 2


def test_inline_active_target_pattern(tmp_path: Path) -> None:
    """Active target on an `Active target:` inline line is detected."""
    _write_control_plane(
        tmp_path,
        textwrap.dedent(
            """\
            # CivicSuite Project Control Plane

            Some preamble.

            Active target: Installer/macOS certification follow-up.

            More text.
            """
        ),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Installer/macOS certification follow-up",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "ALIGNED"


def test_active_work_queue_fallback(tmp_path: Path) -> None:
    """Falls back to ACTIVE_WORK_QUEUE.md when PROJECT_CONTROL_PLANE.md missing."""
    _write_control_plane(
        tmp_path,
        "## Active Target #1\n\nInstaller/macOS certification follow-up\n",
        name="ACTIVE_WORK_QUEUE.md",
    )
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        advances_target="Installer/macOS certification follow-up",
    )
    result = cat.evaluate(manifest, tmp_path)
    assert result.status == "ALIGNED"
