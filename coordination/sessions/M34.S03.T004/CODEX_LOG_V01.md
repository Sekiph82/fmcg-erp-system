# M34.S03.T004 — Corrective-action linkage

Implemented supplier and supplier-evaluation linkage for QMS corrective actions, including validation that an evaluation belongs to the selected supplier, supplier inheritance from linked inspection deviations, supplier-scoped history in Procurement, and permission-aware disclosure and lifecycle controls.

Evidence and verification:
- Audited the applicable GAP-009 supplier-management and GAP-017 QMS findings and implementation notes.
- Added migration `20261104_0001_supplier_corrective_action_linkage.py` with nullable links, indexes, and foreign keys.
- `python -m pytest backend/tests/test_m34_s03_t004_supplier_capa.py -q`: 3 passed.
- Disposable PostgreSQL 16.6 run V06: full Alembic upgrade, task DB tests (2 passed), downgrade to `20261030_0010`, re-upgrade to head, and `alembic current` at `20261104_0001` all passed. Task-owned container cleanup verified. Transcript: `disposable-postgres-run-V06.log`.
- `python -m ruff check ...`: passed for the two task tests and migration; `python -m py_compile ...`: passed for changed backend modules, tests, and migration.
- `npm run type-check` in `frontend`: passed. Targeted supplier page ESLint passed earlier in this task.
- `git diff --check`: passed.
- Independent read-only review identified and the implementation corrected permission-before-write and supplier CAPA lifecycle bypasses (verification/closure and verified-status reversion). The reviewer reported no remaining findings after follow-up.

Iteration notes: earlier disposable runs exposed a test harness role assignment issue, an incorrect open-CAPA count expectation, and downgrade constraint-name assumptions under the repository's metadata-created baseline. These were corrected; V06 is the successful final migration round-trip and acceptance run. No owner records or production database were used.
