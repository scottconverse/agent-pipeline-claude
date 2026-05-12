# CivicCast — Unified Spec (v2, fixture)

> **Note:** This is a stripped-down fixture replica. The real CivicCast spec is much longer; this version exists so the manifest-drafter has a realistic spec-shaped target to walk during plugin tests.

## What CivicCast is

CivicCast is an open-source, self-hostable civic broadcast platform. Streaming-first product with three-tier publish (portal + Internet Archive + syndication). Apache 2.0 / CC BY 4.0 throughout. No appliances, no per-minute fees, no vendor lock-in.

## Source-of-truth documents

- `CivicCastUnifiedSpec-v2.md` (this file) — what the product is, what it does, what its non-negotiables are.
- `CivicCast-ReleasePlan-0.1-to-1.0.md` — what to build, in what order, with what exit criteria.

ADRs live in `docs/adr/`. The verification log template lives in `docs/templates/verification-log.md`. Every accepted ADR is referenced from this file and from the release plan.

## Non-negotiables

- User-facing surfaces follow WCAG 2.2 AA.
- AI artifacts require operator approval before publish.
- Prohibited uses (voice cloning, sentiment scoring of named individuals, biometric ID) never ship.
- Every release ships with the full doc artifact set.
- Test gates green before tag.
- Three-tier archival: every public-record meeting publishes to portal + IA + local NAS before archive-complete.

## Tooling

Python 3.12+. Ruff. Mypy --strict on service modules. Pytest + hypothesis. PostgreSQL 17 + pgvector. Alembic migrations. Apache 2.0 + CC BY 4.0. Conventional Commits + DCO sign-off.
