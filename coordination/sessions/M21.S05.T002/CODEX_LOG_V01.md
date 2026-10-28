# M21.S05.T002 — MPS/MRP integration tests

## Scope

Added a disposable-PostgreSQL integration test for the completed-MRP to MPS plan flow. It verifies source result linkage and generated quantity, then feeds the generated plan through approved BOM material-feasibility evaluation with configured process loss and gram-to-kilogram conversion.

## Implementation

- Added `backend/tests/test_m21_s05_t002_mps_mrp_integration_db.py`.
- Added `coordination/sessions/M21.S05.T002/run_disposable_mps_mrp_integration.ps1`.
- The test refuses to run unless `M21_DISPOSABLE_TEST_DATABASE=1`, the configured name matches `fmcg_m21_s05_t002_<20 hex chars>`, and the SQLAlchemy URL targets that exact loopback database.
- Test writes are rolled back. The runner uses the locally available PostgreSQL 16 Alpine image, a random task-owned database, loopback-only port binding, no volume mounts, and a task label checked before cleanup.

## Verification

- `python -m py_compile backend/tests/test_m21_s05_t002_mps_mrp_integration_db.py` — passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File ..\coordination\sessions\M21.S05.T002\run_disposable_mps_mrp_integration.ps1` from `backend` — passed; Alembic upgraded the fresh disposable database to head and pytest reported `1 passed`.
- The assertion verified 5.000 KG planned from the linked MRP result; a 10% configured input loss and 1000 G per 1 KG output required 5.5556 KG of material, against 5.4 KG synthetic available stock, producing a 0.1556 KG `MATERIAL_SHORT` diagnostic.
- `git diff --check` — passed.
- Verified no container bearing `codex.task=M21.S05.T002` remained after the runner.
- Independent read-only review found no blocker in test coverage, database isolation, or cleanup.

The initial trial used a 31-day plan range; the existing MPS monthly bucketing creates two 30-day anchored periods for that range. The fixture was narrowed to one 30-day period, after which the final isolated test passed. No production code was changed and no GitHub Actions were run.
