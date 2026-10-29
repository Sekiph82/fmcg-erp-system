# M27.S02.T003 — Finished-goods release gate

## Scope and assumption

Implemented the TASKS.md scope, `M27.S02.T003 — Finished-goods release gate`, using the existing quality-gate, QC inspection, finished-goods receipt, and inventory quarantine flows. No task-specific acceptance document was linked from the TASKS.md row; the applicable context was checked against `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`, `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md`, and `docs/planning/GAP-019_SHELF_LIFE_FEFO_AUDIT.md`.

Synthetic operating assumption: finished goods enter a lot-level quarantine after receipt from a completed production order. When an active mandatory `inventory / ON_FINISHED_GOODS_RELEASE` gate is configured, each linked FINISHED_GOODS template must have an accepted, passed, complete inspection for the same production order and lot before inventory can be unblocked. Any other unresolved mandatory finished-goods inspection for that lot also keeps it blocked. This does not invent a real factory, staff, or test result; test measurements and records are synthetic.

## Changes

- Added the finished-goods release gate target and trigger and reject non-FINISHED_GOODS templates linked to that scope.
- Made the gate check lot/order traceability, every linked template, all required pass/decision flags, and unresolved mandatory inspections while holding the applicable gate and inspection rows for serialization.
- Added template-authoritative QC result specifications and complete parameter enforcement for mandatory finished-goods inspections.
- Made the order QC creator derive product, warehouse, lot, and batch from the finished-goods receipt, create inspections for all active mandatory linked templates, and quarantine the lot before release.
- Guarded the release-quarantine API and service so a failed gate produces no stock-unblock side effects. On success, all finished-goods inspections on the lot have their quarantine and hold flags cleared with the stock release.
- Enforced a safe API lock order: check release authorization on the initial read, acquire the finished-goods gate-scope lock, refresh the inspection under `FOR UPDATE`, and recheck authorization before release. This prevents concurrent releases from acquiring inspection rows before the shared gate lock and avoids holding that shared lock for unauthorized requests.
- Added unit and PostgreSQL integration coverage. The DB integration test creates only synthetic data in a per-run task-owned disposable database.

## Verification

- `python -m compileall -q app/services/qms_service.py app/services/quality_service.py app/api/v1/endpoints/quality.py tests/test_m27_s02_t003_finished_goods_release_gate.py tests/test_m27_s02_t003_finished_goods_release_gate_db.py` — passed.
- `python -m pytest -q tests/test_m27_s02_t003_finished_goods_release_gate.py tests/test_m27_s02_t002_production_gate.py tests/test_m27_s02_t001_receiving_gate.py tests/test_m08_s03_t003_qc_finance_closure.py` — 48 passed, 7 skipped (guarded disposable-DB cases).
- `coordination/sessions/M27.S02.T003/run_disposable_finished_goods_gate_tests.ps1` — passed against fresh PostgreSQL 16, migrations through `20261029_0031`, 1 integration test passed. The runner used a random DB/container name, loopback-only port, no volume mounts, no password, synthetic data, and verified/removes its task-labelled container.
- `git diff --check` — passed.
- Independent read-only review found two actionable risks, both resolved before completion: a concurrent release lock-order deadlock and holding the global gate lock for unauthorized requests. The reviewer rechecked the fixes and reported no remaining actionable issues.

## Evidence files

- `backend/tests/test_m27_s02_t003_finished_goods_release_gate.py`
- `backend/tests/test_m27_s02_t003_finished_goods_release_gate_db.py`
- `coordination/sessions/M27.S02.T003/run_disposable_finished_goods_gate_tests.ps1`
