"""Tests for scripts/check_manifest_paths.py — v1.2.0 manifest-integrity gate."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_manifest_paths as cmp  # type: ignore  # noqa: E402


def _write_manifest(dest: Path, pipeline_run: dict) -> Path:
    dest.write_text(yaml.safe_dump({"pipeline_run": pipeline_run}), encoding="utf-8")
    return dest


def test_all_paths_resolve_passes(tmp_path: Path) -> None:
    """Every allowed_paths entry exists → no findings."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "main.py").write_text("# main", encoding="utf-8")
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {"id": "t", "type": "feature", "allowed_paths": ["src/", "tests/"]},
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert findings == [], f"expected no findings, got: {findings}"


def test_missing_allowed_path_is_flagged(tmp_path: Path) -> None:
    """A path in allowed_paths that doesn't exist is flagged."""
    (tmp_path / "src").mkdir()
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {"id": "t", "type": "feature", "allowed_paths": ["src/", "tests/nope/"]},
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert len(findings) == 1
    assert findings[0].field.endswith("allowed_paths")
    assert "tests/nope" in findings[0].value


def test_authorizing_source_validation(tmp_path: Path) -> None:
    """authorizing_source must point at a real file + valid line number."""
    (tmp_path / ".agent-workflows").mkdir()
    cp = tmp_path / ".agent-workflows" / "PROJECT_CONTROL_PLANE.md"
    cp.write_text("\n".join(f"line {i}" for i in range(1, 21)), encoding="utf-8")
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {
            "id": "t",
            "type": "feature",
            "allowed_paths": [".agent-workflows/"],
            "authorizing_source": ".agent-workflows/PROJECT_CONTROL_PLANE.md:5",
        },
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert findings == []


def test_authorizing_source_line_out_of_range(tmp_path: Path) -> None:
    """authorizing_source with line beyond file length is flagged."""
    (tmp_path / ".agent-workflows").mkdir()
    cp = tmp_path / ".agent-workflows" / "PROJECT_CONTROL_PLANE.md"
    cp.write_text("line 1\nline 2\n", encoding="utf-8")
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {
            "id": "t",
            "type": "feature",
            "allowed_paths": [".agent-workflows/"],
            "authorizing_source": ".agent-workflows/PROJECT_CONTROL_PLANE.md:9999",
        },
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert any("out of range" in f.reason for f in findings)


def test_authorizing_source_missing_file(tmp_path: Path) -> None:
    """authorizing_source pointing at a non-existent file is flagged."""
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {
            "id": "t",
            "type": "feature",
            "allowed_paths": [],
            "authorizing_source": "docs/does-not-exist.md:1",
        },
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert any("does not exist" in f.reason for f in findings)


def test_multi_repo_paths(tmp_path: Path) -> None:
    """target_repos paths must exist and be directories."""
    (tmp_path / "umbrella").mkdir()
    (tmp_path / "sibling-a").mkdir()
    (tmp_path / "sibling-a" / "README.md").write_text("# sibling", encoding="utf-8")
    manifest = _write_manifest(
        tmp_path / "umbrella" / "manifest.yaml",
        {
            "id": "t",
            "type": "module-release",
            "allowed_paths": ["umbrella/"] if False else [],
            "target_repos": [
                {"path": "sibling-a", "allowed_paths": ["README.md"]},
                {"path": "sibling-b-missing", "allowed_paths": ["README.md"]},
            ],
        },
    )
    # Move to tmp_path so the multi-repo resolver can find sibling-a/b-missing relative
    manifest_relocated = tmp_path / "manifest.yaml"
    manifest_relocated.write_text((tmp_path / "umbrella" / "manifest.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    findings = cmp.evaluate(manifest_relocated, tmp_path)
    assert any("sibling-b-missing" in f.value for f in findings)


def test_expected_outputs_lenient(tmp_path: Path) -> None:
    """expected_outputs entries that don't exist yet are OK if parent is allowed."""
    (tmp_path / "src").mkdir()
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {
            "id": "t",
            "type": "feature",
            "allowed_paths": ["src/"],
            "expected_outputs": ["src/new_feature.py"],  # doesn't exist yet, will be created
        },
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert findings == []


def test_expected_output_outside_allowed_is_flagged(tmp_path: Path) -> None:
    """expected_outputs entries outside allowed_paths are flagged."""
    (tmp_path / "src").mkdir()
    manifest = _write_manifest(
        tmp_path / "manifest.yaml",
        {
            "id": "t",
            "type": "feature",
            "allowed_paths": ["src/"],
            "expected_outputs": ["lib/wrong_place.py"],
        },
    )
    findings = cmp.evaluate(manifest, tmp_path)
    assert any("not within any declared allowed_paths" in f.reason for f in findings)
