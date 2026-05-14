"""Unit tests for scripts/validate_scope.py."""

from __future__ import annotations

import textwrap

import pytest

from scripts.validate_scope import validate


VALID_SCOPE = textwrap.dedent("""\
    # Scope contract — 2026-05-14-test

    **Goal**: Fix the auth-timeout bug

    **Mode**: task

    **Branch**: fix/auth-timeout (NEW branch off master)

    **Allowed paths**:
    - backend/auth/

    **Forbidden paths**:
    - docs/adr/

    **Success criteria**:
    - All tests pass (`pytest`)

    **Tasks**:

    1. Patch the timeout constant in backend/auth/jwt.py
       - Description: bump from 24h to 14d
       - Success: test_auth_timeout passes

    **Risk**: low

    **Rollback**: git revert <commit>
    """)


def test_valid_scope_passes():
    assert validate(VALID_SCOPE) == []


def test_missing_goal_caught():
    bad = VALID_SCOPE.replace("**Goal**:", "**Stated objective**:")
    violations = validate(bad)
    assert any("Goal" in v for v in violations)


def test_missing_mode_caught():
    bad = VALID_SCOPE.replace("**Mode**: task", "**Modus**: task")
    violations = validate(bad)
    assert any("Mode" in v for v in violations)


def test_invalid_mode_value_caught():
    bad = VALID_SCOPE.replace("**Mode**: task", "**Mode**: feature")
    violations = validate(bad)
    assert any("Mode" in v and "feature" in v for v in violations)


def test_invalid_risk_value_caught():
    bad = VALID_SCOPE.replace("**Risk**: low", "**Risk**: catastrophic")
    violations = validate(bad)
    assert any("Risk" in v and "catastrophic" in v for v in violations)


def test_no_tasks_caught():
    bad = textwrap.dedent("""\
        **Goal**: Fix
        **Mode**: task
        **Branch**: fix/x
        **Allowed paths**: backend/
        **Forbidden paths**: docs/adr/
        **Success criteria**: tests pass
        **Tasks**:
        (none yet)
        """)
    violations = validate(bad)
    assert any("Tasks" in v and "numbered" in v.lower() for v in violations)


def test_sprint_mode_accepted():
    sprint = VALID_SCOPE.replace("**Mode**: task", "**Mode**: sprint")
    assert validate(sprint) == []


def test_risk_optional_when_absent():
    # Drop the **Risk** line entirely — it's optional
    no_risk = "\n".join(ln for ln in VALID_SCOPE.splitlines() if "**Risk**" not in ln)
    # Should pass — Risk isn't in REQUIRED_FIELDS
    violations = validate(no_risk)
    assert all("Risk" not in v for v in violations)
