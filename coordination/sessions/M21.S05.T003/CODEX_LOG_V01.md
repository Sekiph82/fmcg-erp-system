# M21.S05.T003 — Costing integration tests

## Acceptance basis

The canonical `TASKS.md` row names integration coverage and has no separate linked acceptance file. The adjacent M21.S02.T003/T004 evidence defines the implemented rule: recipe-standard loss is snapshotted per waste row, its cost exposure is informational, and it remains outside finalized component and total cost. No additional costing policy was introduced.

## Implementation

- Added `backend/tests/test_m21_s05_t003_costing_integration_db.py` using real PostgreSQL rows for a completed synthetic production order, product, material standard cost, and recipe-standard waste snapshot.
- Added `coordination/sessions/M21.S05.T003/run_disposable_costing_integration.ps1`.
- The integration calls `compute_order_cost`, `finalize_order_cost`, and `get_cost_report`. It verifies that a 12 KG actual loss against a 10% standard on 100 KG expected output, priced at 5 KES/KG, produces a 10 KES informational variance while finalized and reported `total_cost` remains 0.
- The database test requires `M21_DISPOSABLE_TEST_DATABASE=1`, an exact random task-specific database name, and a loopback PostgreSQL URL; its writes roll back.
- The runner uses the locally available PostgreSQL 16 Alpine image, one random task-labeled disposable database, an ephemeral loopback-only host port, no volume mounts, and checks the exact task label before cleanup.

## Verification

- `python -m py_compile tests/test_m21_s05_t003_costing_integration_db.py` — passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File ..\coordination\sessions\M21.S05.T003\run_disposable_costing_integration.ps1` from `backend` — passed; fresh database migrated to Alembic head and pytest reported `1 passed`.
- Verified no container bearing `codex.task=M21.S05.T003` remained.
- `git diff --check` — passed.
- Independent read-only review found no blocker in coverage, financial separation, database isolation, or cleanup.

No production code, production data, finalized cost policy, or GitHub Actions were changed or used.
