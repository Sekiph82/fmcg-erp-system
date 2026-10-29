# M27.S02.T004 — Dispatch gate

## Scope and assumption

Implemented the exact TASKS.md task, `M27.S02.T004 — Dispatch gate`. No task-specific acceptance document was linked from its TASKS.md row. The applicable dispatch and quality context was checked against `docs/planning/GAP-010_CRM_SALES_PIPELINE_AUDIT.md`, `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md`, `docs/planning/GAP-019_SHELF_LIFE_FEFO_AUDIT.md`, and `docs/planning/GAP-SEC-001_ACCESS_CONTROL_AUDIT.md`.

Synthetic operating assumption: an active mandatory `sales / ON_DISPATCH` quality gate requires each shipment line to identify a finished-goods lot with accepted, passed inspection records for every linked FINISHED_GOODS QC template. Any other unresolved mandatory finished-goods inspection on that product/warehouse/lot prevents dispatch. Dispatch without active mandatory gate configuration preserves the existing flow. This uses only synthetic shipment, lot, QC, and stock data in tests; it does not represent a real customer, factory, or approval.

## Changes

- Added the sales `ON_DISPATCH` gate scope and reject templates other than FINISHED_GOODS for this scope.
- Added dispatch validation for every shipment line: require lot traceability, a completed accepted/passed inspection for each active mandatory linked template, and no unresolved mandatory finished-goods inspection for the same product/warehouse/lot.
- Serialize dispatch against gate configuration changes and lock the accepted/unresolved inspections before stock mutations.
- Include active dispatch-gate templates when the finished-goods QC creator determines which inspections to create, alongside finished-goods-release templates.
- Run the dispatch gate before stock depletion, movement creation, shipment status changes, or sales-order shipped quantity changes. A failed gate returns 422 and the caller's transaction leaves all those effects unchanged.
- Kept gate evaluation within the existing dispatch transaction, so a successful stock ISSUE, shipment transition, and sales-order line update commit together.

## Verification

- `python -m compileall -q app/services/qms_service.py app/services/quality_service.py app/services/sales_service.py tests/test_m27_s02_t004_dispatch_gate.py tests/test_m27_s02_t004_dispatch_gate_db.py` — passed.
- `python -m pytest -q tests/test_m27_s02_t004_dispatch_gate.py tests/test_m27_s02_t003_finished_goods_release_gate.py tests/test_m27_s02_t002_production_gate.py tests/test_m27_s02_t001_receiving_gate.py tests/test_m08_s03_t003_qc_finance_closure.py` — 54 passed, 7 skipped (guarded disposable-DB cases).
- `coordination/sessions/M27.S02.T004/run_disposable_dispatch_gate_tests.ps1` — passed against fresh PostgreSQL 16, migrations through `20261029_0031`, 1 integration test passed. The runner used a random database/container name, loopback-only port, no volume mounts, no password, synthetic data, and verified/removes its task-labelled container.
- Independent read-only review: no material correctness, security, or transaction findings.
- `git diff --check` — passed.

## Evidence files

- `backend/tests/test_m27_s02_t004_dispatch_gate.py`
- `backend/tests/test_m27_s02_t004_dispatch_gate_db.py`
- `coordination/sessions/M27.S02.T004/run_disposable_dispatch_gate_tests.ps1`
