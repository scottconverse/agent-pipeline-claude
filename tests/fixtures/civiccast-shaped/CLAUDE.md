# CivicCast — Project Instructions for Claude Code (fixture)

> **Fixture replica.** The real CivicCast CLAUDE.md is longer.

## Source-of-truth documents

1. `CivicCastUnifiedSpec-v2.md`
2. `CivicCast-ReleasePlan-0.1-to-1.0.md`

ADRs in `docs/adr/`. Per-rung scope-locks in `docs/releases/v<version>-scope-lock.md`. Per-feature design notes in `docs/research/v<version>-<feature>-design.md`.

## Pipeline drafter notes

The manifest-drafter for `agent-pipeline-claude` reads these paths in this project:

- **Project spec:** `CivicCastUnifiedSpec-v2.md` (root).
- **Release ladder:** `CivicCast-ReleasePlan-0.1-to-1.0.md` (root).
- **Per-rung scope contract:** `docs/releases/v<rung>-scope-lock.md`.
- **Per-feature design notes:** `docs/research/v<rung>-<feature>-design.md`.
- **Audit ledgers:** `audit-civiccast-*/` directories at root; per-commit findings in `audit-civiccast-*/0X-<role>-deepdive.md`.
- **Findings cleanup queue:** `next-cleanup.md` at root.
- **Live status:** `HANDOFF.md` at root (gitignored).

When drafting a manifest, the drafter should quote the matching scope-lock + design note verbatim where the source has the right shape; paraphrase only when the source is too long.

## Git workflow

- One branch per rung: `rung/0.X-name` (e.g. `rung/0.4`).
- Conventional Commits + DCO sign-off on every commit.
- Each rung's PR is the rung's release. The verification log goes in the PR description.
- Tag `v0.X.0` after merge to `main`. Push the tag only after director confirms.

## Order of operations

1. Read the spec section relevant to the change.
2. Locate the change in the current rung of the release plan.
3. State approach before writing code.
4. Build to production quality on the first pass.
5. Apply the layered audit pattern (per-commit careful-coding, per-checkpoint sanity sweep, per-rung audit-lite, per-release audit-team).
6. Tag the rung version after audit-lite clean + verification log signed.

## Tooling

Python 3.12+. Ruff. Mypy. Pytest + hypothesis. PostgreSQL 17. Conventional Commits + DCO.

## Non-negotiables

See `CivicCastUnifiedSpec-v2.md` § Non-negotiables. The floor, not aspirations.
