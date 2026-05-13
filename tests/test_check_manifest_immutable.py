"""Tests for scripts/check_manifest_immutable.py — v1.2.0 D1 cross-stage integrity gate."""

from __future__ import annotations

from pathlib import Path

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_manifest_immutable as cmi  # type: ignore  # noqa: E402


def _setup_run(tmp_path: Path, manifest_content: str = "manifest: original\n") -> Path:
    run_dir = tmp_path / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.yaml").write_text(manifest_content, encoding="utf-8")
    return run_dir


def test_pin_then_check_passes(tmp_path: Path) -> None:
    """Pin captures SHA, check against unchanged manifest passes."""
    run_dir = _setup_run(tmp_path)
    rc, msg = cmi.pin(run_dir)
    assert rc == 0
    assert (run_dir / "manifest.sha").exists()
    rc, msg = cmi.check(run_dir)
    assert rc == 0, msg


def test_check_fails_on_mutation(tmp_path: Path) -> None:
    """If manifest changes after pin, check returns MANIFEST_MUTATED (exit 1)."""
    run_dir = _setup_run(tmp_path)
    cmi.pin(run_dir)
    # Mutate the manifest
    (run_dir / "manifest.yaml").write_text("manifest: mutated\n", encoding="utf-8")
    rc, msg = cmi.check(run_dir)
    assert rc == 1
    assert "MANIFEST_MUTATED" in msg


def test_check_without_pin_fails_gracefully(tmp_path: Path) -> None:
    """check without prior pin returns exit 2 (pin file missing)."""
    run_dir = _setup_run(tmp_path)
    rc, msg = cmi.check(run_dir)
    assert rc == 2
    assert "pin file not found" in msg


def test_pin_without_manifest_fails(tmp_path: Path) -> None:
    """pin against missing manifest returns exit 2."""
    run_dir = tmp_path / ".agent-runs" / "empty"
    run_dir.mkdir(parents=True)
    rc, msg = cmi.pin(run_dir)
    assert rc == 2
    assert "manifest not found" in msg


def test_sha_is_stable(tmp_path: Path) -> None:
    """SHA-256 of the same manifest content is stable across pins."""
    run_dir1 = _setup_run(tmp_path / "a", "stable: yes\n")
    run_dir2 = _setup_run(tmp_path / "b", "stable: yes\n")
    cmi.pin(run_dir1)
    cmi.pin(run_dir2)
    sha1 = (run_dir1 / "manifest.sha").read_text(encoding="utf-8").strip().split()[0]
    sha2 = (run_dir2 / "manifest.sha").read_text(encoding="utf-8").strip().split()[0]
    assert sha1 == sha2
