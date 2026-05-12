# v0.4 Slice 1 — Broadcast Spine Design (fixture)

> **Fixture replica.** A real design note is longer.

## Scope

Backend data spine + contracts for the v0.4 live-broadcast surface. No operator UI, no resident UI in Slice 1.

## QA-005 — conflict-409 race when conflicting row is cancelled mid-lookup

### Problem

The schedule create endpoint checks for conflicting items at request time. Between the conflict-check SELECT and the row INSERT, a concurrent transaction can transition the conflicting item to `cancelled`. The original request then surfaces an HTTP 409 citing a row that no longer exists in `state = scheduled`, confusing operators.

### Fix

Inside the schedule store's `create` transaction:

1. Re-run the conflict check inside the same SERIALIZABLE transaction immediately before INSERT.
2. If the conflict has cleared (peer item is now `cancelled` or `published`), proceed with the INSERT.
3. If the conflict still holds, raise `ScheduleConflictError` with `conflicting_item` populated.

### Test

- New real-Postgres test `tests/schedule/test_real_postgres.py::TestQA005ConflictRetry` with `threading.Barrier(2)`. Two transactions race: one cancels the conflicting item, the other tries to create. Assert: the create succeeds; no 409 is raised; the second transaction sees the cancellation.

### Exit criteria

- New `tests/schedule/test_real_postgres.py::TestQA005ConflictRetry` passes against real Postgres.
- Existing `tests/schedule/test_metadata_edit.py::TestUpdateMetadataPublishedGuard` remains green.
- Audit-team ledger row QA-005 flips from Major-open to Closed.

## QA-007 — TOCTOU edit-trim button + state guard at update_metadata

### Problem

The operator can click "Edit Trim" on an asset whose linked schedule item has been transitioned to `published` between the operator's last list-refresh and the click. The PATCH `/api/staff/assets/{id}` endpoint accepts the edit, mutating an asset whose schedule item already exists in published state — silently making the published item inconsistent with the asset it links to.

### Fix

In `civiccast/schedule/store.py::update_metadata`:

1. Open a transaction.
2. Look up the asset row.
3. Look up any linked schedule items in state `published` (`schedule_items WHERE asset_id = ? AND state = 'published'`).
4. If any exist, raise `AssetAlreadyPublishedError(asset_id=<id>, published_schedule_item_ids=[<ids>])`.
5. Otherwise proceed with the metadata update.

Router maps `AssetAlreadyPublishedError` to HTTP 409 with detail body `{message, published_schedule_item_ids}`.

### Test

- New `tests/schedule/test_metadata_edit.py::TestUpdateMetadataPublishedGuard::test_refused_when_asset_has_published_schedule_item`.
- New `tests/schedule/test_metadata_edit.py::TestUpdateMetadataPublishedGuard::test_allowed_when_only_cancelled_or_scheduled`.
- New real-Postgres race test for the publish-during-update window.

### Exit criteria

- All three new tests pass.
- Audit-team ledger row QA-007 flips from Major-open to Closed.
- The TOCTOU window in `update_metadata` is closed — researcher confirms via static-trace before signing off.

## Files affected

- `civiccast/schedule/store.py` (new exception + guard + retry).
- `civiccast/schedule/router.py` (409 mapping for `AssetAlreadyPublishedError`).
- `tests/schedule/test_metadata_edit.py` (3 new tests).
- `tests/schedule/test_real_postgres.py` (1 new real-Postgres test).
- `CHANGELOG.md` ([Unreleased] entry).
