# M20.S01.T001 V04 Codex Implementation Log

## Status

`AWAITING_CHATGPT_AUDIT`

Builder: Codex
Implementation commit: `158d281` (`fix(mps): make MPS release atomic and sequence-safe`)
Base audited: `111aecd`

## Synchronization and Safety

- Local `main` was fast-forwarded from `ab4c214` to the current GitHub `main` commit `111aecd`.
- No reset, clean, stash, rebase, force-push, or new branch was used.
- The pre-existing dirty owner worktree was preserved.
- `TASKS.md`, `TASKS_HISTORY.md`, and all `CHATGPT_AUDIT_*` files were not modified.
- Only the M20.S01.T001 implementation/test files were included in commit `158d281`.

## V04 Findings Addressed

### F-V03-001: real transaction rollback proof

Replaced the V03 fake transaction test with a PostgreSQL integration test that creates persisted MPS fixtures, injects a late flush failure inside the release transaction, and verifies from a separate session that the ProductionOrder count, MPSLine linkage, and MPSPlan status are rolled back.

The same test skips when PostgreSQL is unavailable locally. Docker was unavailable on this workstation because the Docker Linux engine pipe was not running. The CI workflow already provides a PostgreSQL service, so this test is intended to execute there.

### F-V03-002: clean base/head regression comparison

The identical regression command was run in clean detached worktrees:

```text
python -m pytest tests/ -k "mps or mrp or module_registry or gap007 or gap015 or permission or recipe or warehouse or production" -q -p no:warnings
```

Exact base `111aecd`: `173 passed, 4 failed, 471 deselected`.

Exact V04 head `158d281`: `173 passed, 3 failed, 2 skipped, 471 deselected`.

The base-only MPS failure was the obsolete expectation that an eligible line could create a PO while two ineligible lines remained. The test was updated for the V04 all-or-none contract. The three remaining failures are unchanged at base/head and are in GAP-012, GAP-013, and GAP-014 route-wrapper tests (`_IncludedRouter` has no `.path`). They are outside this remediation scope.

### F-V03-003: partial release and retry behavior

`release_mps_plan` now preflights every positive unreleased feasible line, including effective approved recipe and authoritative product UOM validation, before adding or flushing any ProductionOrder. If a recipe is missing or any positive unreleased line is ineligible, the service returns zero newly released orders, keeps the plan `APPROVED`, preserves truthful unresolved counters, and allows a repaired plan to be retried.

The V02/V03 unit coverage and the existing hardening test now assert this all-or-none behavior.

### F-V03-004: ProductionOrder number collision risk

MPS PO numbering now counts only `PO-MPS-*` orders and, on PostgreSQL, takes a transaction-level advisory lock before allocation. Concurrent MPS releases therefore serialize the allocator while the existing unique constraint remains the final database guard. A PostgreSQL concurrency test runs two concurrent releases and asserts two distinct `PO-MPS-*` numbers; it skips locally when the PostgreSQL service is unavailable.

## Files Changed

- `backend/app/services/mps_service.py`
- `backend/tests/test_m20_s01_t001_mps_hardening.py`
- `backend/tests/test_m20_s01_t001_v02_mps_remediation.py`
- `backend/tests/test_m20_s01_t001_v03_mps_remediation.py`
- `coordination/sessions/M20-S01-T001/CODEX_LOG_V04.md`

## Checks Run

- `python -m py_compile app/services/mps_service.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py` — passed.
- `python -m pytest tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py -q` — `20 passed, 2 skipped`.
- `python -m alembic heads` — one head: `20260602_0001`.
- `git diff --check` on scoped implementation/test files — passed.
- Clean exact-base regression — `173 passed, 4 failed, 471 deselected`.
- Clean exact-V04-head regression — `173 passed, 3 failed, 2 skipped, 471 deselected`.
- Docker/PostgreSQL local probe — unavailable; Docker daemon pipe was not running.

## Known Limitations

- The two PostgreSQL-backed tests were not executed locally because the required database service was unavailable. They remain active tests and are designed for the repository CI PostgreSQL service.
- The three unchanged GAP-012/013/014 route-wrapper regression failures remain for independent audit/triage.
- No migration was required; the implementation uses the existing `ProductionOrder.order_no` unique constraint and PostgreSQL transaction advisory locking.

## Acceptance Snapshot

- [x] V04 implementation is committed on `main`.
- [x] All-or-none release behavior is implemented and unit-tested.
- [x] PostgreSQL rollback and concurrent numbering tests are present.
- [x] Clean base/head comparison is recorded.
- [x] Protected tracker and ChatGPT audit files were not modified.
- [ ] Independent ChatGPT audit and acceptance pending.
