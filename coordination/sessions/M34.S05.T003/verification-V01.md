# M34.S05.T003 verification

## Scope

The task adds one authenticated FastAPI/PostgreSQL integration scenario across procurement receipt, three-way invoice matching, and finance posting. It uses only synthetic records and a task-specific disposable database. No product behavior or live business data was changed.

## Evidence

- `disposable-postgres-run-V04.log`: PostgreSQL 16.6, exact task-prefixed database, passwordless trust authentication bound to `127.0.0.1`, Alembic `upgrade head`, and the task-guarded pytest module: **1 passed**.
- `container-cleanup-V04.log`: task-owned container removed and exact-name absence verified.
- SHA-256 of the retained local V04 runner transcript: `3B69591BC0B5DF81EC194E89A0B2B065E5B0D6AB2C8DC71C0EBA39CDEA4744F0`.
- `python -m py_compile backend/tests/test_m34_s05_t003_three_way_finance_workflow_db.py`: passed.
- `git diff --check`: passed.
- Ruff was not available in the backend virtual environment (`No module named ruff`); no Ruff pass is claimed.

The integration test uses a signed test JWT and synthetic TOTP enrollment to exercise authenticated API routes. It verifies that a draft GRN leaves the invoice blocked and creates no finance event; posting the GRN through the procurement API updates stock/PO receipt state; a rerun of the three-way match becomes payable and links the accepted GRN quantity; finance API posting creates a balanced journal and one operational posting event; replay returns the same event. Invoice lifecycle status remains `RECEIVED` until the separate payment lifecycle changes it.

## Limits

This test does not cover interactive password login or completing a live 2FA challenge, supplier payment execution, landed cost, or production data. It does not run GitHub Actions.

## Independent review

Independent read-only review found no blocking/actionable findings. The reviewer recommended asserting that the initial hold reason names the draft GRN; the assertion was added and the V04 fresh-database run passed.
