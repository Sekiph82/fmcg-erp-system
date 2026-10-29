# M10.S02.T004 — Codex implementation evidence

**Status:** COMPLETE — implementation and focused checks passed; independent read-only review found no actionable issue.

**Scope:** Serialize concurrent lot hold/release status creation and mutation, and enforce existing quality permissions plus warehouse scope before either API mutation.

## Implemented

- Replaced the select-then-insert lot-status path with PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` on the unique `lot_id`, followed by `SELECT ... FOR UPDATE`. A concurrent first writer now waits on the unique key, and subsequent mutations serialize on the single per-lot status row until the caller commits or rolls back.
- Added an authorization check to the lot hold and release API routes. Existing broad quality edit permission authorizes holds; existing broad quality approval/release permissions authorize releases. Scoped users must have the matching quality action and warehouse action for every distinct warehouse currently holding the lot.
- Because `LotQualityStatus` is one record shared by all warehouses for a lot, partial warehouse scope is rejected. A lot with no stock warehouse association requires broad quality permission; a scoped permission alone cannot mutate that shared status.
- Added permission tests for broad access, fully covered scoped hold/release, partial-scope denial, and unstocked-lot denial. Added PostgreSQL transaction tests for concurrent first hold/release and rollback of an uncommitted status row.

## Verification

- `python -m pytest backend/tests/test_m10_s02_t004_lot_hold_release_access.py backend/tests/test_m10_s02_t004_lot_hold_release_transaction_db.py -q` without the disposable-database flag — **5 passed, 2 skipped**. The two skipped cases are deliberately gated to the task-owned disposable PostgreSQL database.
- Disposable loopback PostgreSQL 16 database named `fmcg_m10_s02_t004_<random hex>`: `alembic upgrade head` — passed; the two database-backed tests, together with the five permission tests — **7 passed**. The disposable container was removed in the command's `finally` block.
- `python -m compileall -q` for the changed service, endpoint, and tests — passed.
- `git diff --check` — passed.
- Independent read-only review by `/root/m08_transition_review` found no actionable issues in the permission/scope gate or row-lock transaction changes. The reviewer did not modify files or run tests/database operations.

## Limits

- No production or owner database was accessed. Database writes were synthetic and confined to the named disposable database, which was removed afterward.
- The implementation reuses existing permission and scope records; it does not create roles, permissions, warehouse assignments, or business policy.
- No GitHub Actions, deployment, merge, or production approval is claimed.
