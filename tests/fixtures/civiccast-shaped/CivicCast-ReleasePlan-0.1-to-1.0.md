# CivicCast — Release Plan 0.1 to 1.0 (fixture)

> **Fixture replica.** The real CivicCast release plan is much longer; this version exists so the manifest-drafter has a realistic release-ladder target.

## Rungs

| Rung | Theme | Status |
| :--- | :--- | :--- |
| 0.1 | Foundation | shipped |
| 0.2 | Stream substrate | shipped |
| 0.3 | Assets + scheduling | shipped (v0.3.1) |
| 0.4 | Broadcast Spine And Contracts | in flight |
| 0.5 | Captions | queued |
| 0.6 | Summary + signed PDF/A | queued |
| 0.7 | Archive (IA + NAS) | queued |
| 0.8 | Syndication + ActivityPub | queued |
| 0.9 | Translation | queued |
| 0.10 | Polish + audit-team burn-down | queued |
| 1.0 | First stable release | queued |

## Rung 0.4 — Broadcast Spine And Contracts

Five slices (per scope-lock at `docs/releases/v0.4-scope-lock.md`):

1. Slice 1 — Broadcast spine + contracts (in flight; commits 1-7 landed, commits 8-9 remaining).
2. Slice 2 — Operator Live Room (queued).
3. Slice 3 — Resident Portal And Recording Completion (queued).
4. Slice 4 — Trim Precision And Packager Truth (queued).
5. Slice 5 — v0.4 Release Gate (queued).

### Slice 1 remaining commits

- Commit 8 — QA-005 conflict-409 race retry + QA-007 linked-published-schedule guard.
- Commit 9 — TEST-004/006/008/009 promotions + ADR 0010 + ADR 00NN + civiccast/live/README.md.
