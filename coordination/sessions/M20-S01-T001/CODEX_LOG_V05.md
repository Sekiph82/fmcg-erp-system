# M20.S01.T001 V05 Codex Implementation Log

## Status

`AWAITING_CHATGPT_AUDIT`

Builder: Codex
Start source: `f8f6404`
Implementation commit: `16c4bea`
Published main head: `ef85f9a`
Pending PostgreSQL CI run: https://github.com/Sekiph82/fmcg-erp-system/actions/runs/39284832263

## Scope and Safety

- GitHub `main` was fetched and the existing owner dirty worktree was preserved.
- No reset, clean, stash, rebase, force-push, or new branch was used.
- GitHub’s intervening V05 prompt/tracker commits were integrated with a normal merge before push.
- `TASKS.md` was not edited by Codex; the upstream V05 tracker update was preserved.
- `TASKS_HISTORY.md` and all `CHATGPT_AUDIT_*` files were not modified.

## V05 Corrections

### PostgreSQL rollback and concurrency fixtures

The real PostgreSQL tests in `test_m20_s01_t001_v03_mps_remediation.py` were corrected to flush Product and Warehouse rows before constructing Recipe and MPSLine foreign-key references. The rollback test uses a real `AsyncSession`, the actual release endpoint transaction boundary, an injected late flush failure after the first PO flush, and an independent verification session for PO count, line linkage, and plan status.

The concurrency test runs two real release calls concurrently, verifies distinct committed `PO-MPS-*` numbers and released linkage, deletes one produced order, then retries a new release and verifies the number remains above the deleted high-water mark.

### Collision-safe monotonic numbering

The previous `count(PO-MPS-*) + 1` allocator was replaced with a PostgreSQL sequence named `mps_po_number_seq`. Migration `20261019_0010_mps_po_number_sequence` initializes the sequence from the existing numeric `PO-MPS-*` maximum and preserves monotonicity after deletion. MPS release uses `nextval()` and does not alter unrelated production-order numbering.

### Migration

Alembic now has one head, `20261019_0010`.

## Changed Files

- `backend/app/services/mps_service.py`
- `backend/alembic/versions/20261019_0010_mps_po_number_sequence.py`
- `backend/tests/test_m20_s01_t001_v03_mps_remediation.py`
- `coordination/sessions/M20-S01-T001/CODEX_LOG_V05.md`

## Local Verification

All local commands below ran from a clean detached worktree at published head `ef85f9a`, except where noted as a CI-only proof.

- `python -m py_compile app/services/mps_service.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py alembic/versions/20261019_0010_mps_po_number_sequence.py` — passed.
- `python -m compileall -q app` — passed.
- `python -m alembic heads` — one head: `20261019_0010`.
- `git diff --check` on scoped V05 files — passed.
- `python -m pytest tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t001_mps_hardening.py -q` — `37 passed, 2 skipped`.
- Clean regression: `python -m pytest tests/ -k "mps or mrp or module_registry or gap007 or gap015 or permission or recipe or warehouse or production" -q -p no:warnings` — `173 passed, 3 failed, 2 skipped, 471 deselected`.

## PostgreSQL Evidence State

`BLOCKED_DB_PROOF`: the local Docker PostgreSQL daemon is unavailable, so the two real database tests skipped locally. GitHub Actions run `39284832263` was queued at log publication time and has not yet produced pass/fail/skip evidence. No PostgreSQL rollback or concurrency PASS is claimed here. The CI workflow contains a PostgreSQL 16 service and will execute the tests when the queued run starts.

## Regression Attribution and Risks

The three clean-head regression failures are unchanged GAP-012, GAP-013, and GAP-014 route-wrapper failures: the tests access `.path` on an `_IncludedRouter`. They are outside M20.S01.T001 and were not weakened or silently changed.

The remaining acceptance blocker is independently verifiable PostgreSQL execution of rollback, concurrent allocation, and deletion-gap tests. ChatGPT audit should inspect the CI run and artifacts before accepting T001.

## Acceptance Snapshot

- [x] V05 implementation committed and pushed to `main`.
- [x] Monotonic sequence migration added and single Alembic head verified locally.
- [x] Real rollback, concurrency, and deletion-gap tests present.
- [x] Clean base/head regression issues attributed without weakening tests.
- [x] Protected tracker and ChatGPT audit files untouched by Codex.
- [ ] PostgreSQL runtime proof pending GitHub Actions run.
- [ ] Independent ChatGPT audit and tracker acceptance pending.
